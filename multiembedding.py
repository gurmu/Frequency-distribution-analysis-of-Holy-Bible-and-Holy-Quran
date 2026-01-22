import os
import requests
import json
from typing import Any, Dict

# ----------------------------
# REQUIRED CONFIG (fill these)
# ----------------------------
SEARCH_ENDPOINT = "https://itsmmulti.search.azure.us"
SEARCH_ADMIN_KEY = os.getenv("AZSEARCH_ADMIN_KEY", "PASTE_ADMIN_KEY_HERE")

# Storage connection for datasource + knowledge store:
# Use ResourceId-based connection string (good for Managed Identity scenarios)
STORAGE_RESOURCE_ID = os.getenv(
    "AZ_STORAGE_RESOURCE_ID",
    "ResourceId=/subscriptions/<SUB>/resourceGroups/rg-itsm-multiagent-dev/providers/Microsoft.Storage/storageAccounts/stitsmdevz33lh8/;"
)

# Azure Vision / Foundry endpoint for multimodal embedding skill
COGNITIVE_SERVICES_URL = os.getenv(
    "AZ_VISION_FOUNDRY_ENDPOINT",
    "https://<your-foundry-or-vision-endpoint>/"
)

MODEL_VERSION = "2023-04-15"
API_VERSION = "2025-11-01-preview"

SOURCE_CONTAINER = "itsm-kb"               # your DOCX container
IMAGE_PROJECTION_CONTAINER = "itsm-kb-images"

DATASOURCE_NAME = "itsm-docx-mm-ds"
INDEX_NAME = "itsm-docx-mm-index"
SKILLSET_NAME = "itsm-docx-mm-skillset"
INDEXER_NAME = "itsm-docx-mm-indexer"

# ----------------------------
# HTTP helpers
# ----------------------------
HEADERS = {
    "Content-Type": "application/json",
    "api-key": SEARCH_ADMIN_KEY
}

def put(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{SEARCH_ENDPOINT}{path}?api-version={API_VERSION}"
    r = requests.put(url, headers=HEADERS, data=json.dumps(payload))
    if r.status_code not in (200, 201):
        raise RuntimeError(f"PUT {url} failed: {r.status_code}\n{r.text}")
    return r.json()

def post(path: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    url = f"{SEARCH_ENDPOINT}{path}?api-version={API_VERSION}"
    r = requests.post(url, headers=HEADERS, data=json.dumps(payload) if payload else None)
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"POST {url} failed: {r.status_code}\n{r.text}")
    return r.json() if r.text else {}

def get(path: str) -> Dict[str, Any]:
    url = f"{SEARCH_ENDPOINT}{path}?api-version={API_VERSION}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        raise RuntimeError(f"GET {url} failed: {r.status_code}\n{r.text}")
    return r.json()

# ----------------------------
# 1) Data Source (Blob)
# ----------------------------
datasource = {
    "name": DATASOURCE_NAME,
    "type": "azureblob",
    "credentials": {
        "connectionString": STORAGE_RESOURCE_ID
    },
    "container": {
        "name": SOURCE_CONTAINER
    }
}

# ----------------------------
# 2) Index (vector + text + image path)
# NOTE: dimensions=1024 matches the tutorial
# ----------------------------
index = {
    "name": INDEX_NAME,
    "fields": [
        {"name": "content_id", "type": "Edm.String", "key": True, "retrievable": True, "analyzer": "keyword"},
        {"name": "text_document_id", "type": "Edm.String", "filterable": True, "retrievable": True, "stored": True},
        {"name": "image_document_id", "type": "Edm.String", "filterable": True, "retrievable": True},

        {"name": "document_title", "type": "Edm.String", "searchable": True},
        {"name": "content_text", "type": "Edm.String", "searchable": True, "retrievable": True},
        {"name": "content_path", "type": "Edm.String", "retrievable": True},

        {
            "name": "content_embedding",
            "type": "Collection(Edm.Single)",
            "dimensions": 1024,
            "searchable": True,
            "retrievable": True,
            "vectorSearchProfile": "hnsw"
        },
        {
            "name": "location_metadata",
            "type": "Edm.ComplexType",
            "fields": [
                {"name": "page_number", "type": "Edm.Int32", "retrievable": True},
                {"name": "bounding_polygons", "type": "Edm.String", "retrievable": True}
            ]
        }
    ],
    "vectorSearch": {
        "profiles": [
            {"name": "hnsw", "algorithm": "defaulthnsw", "vectorizer": "vision-mm-vectorizer"}
        ],
        "algorithms": [
            {
                "name": "defaulthnsw",
                "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"}
            }
        ],
        "vectorizers": [
            {
                "name": "vision-mm-vectorizer",
                "kind": "aiServicesVision",
                "aiServicesVisionParameters": {
                    "resourceUri": COGNITIVE_SERVICES_URL,
                    "authIdentity": None,
                    "modelVersion": MODEL_VERSION
                }
            }
        ]
    }
}

# ----------------------------
# 3) Skillset (extract -> split -> vectorize text & images -> shape)
# ----------------------------
skillset = {
    "name": SKILLSET_NAME,
    "description": "Multimodal DOCX indexing: extract text/images, chunk text, embed both, project to index + knowledge store",
    "skills": [
        {
            "@odata.type": "#Microsoft.Skills.Util.DocumentExtractionSkill",
            "name": "document-extraction-skill",
            "description": "Extract text and images from Office/PDF docs",
            "parsingMode": "default",
            "dataToExtract": "contentAndMetadata",
            "configuration": {
                "imageAction": "generateNormalizedImages",
                "normalizedImageMaxWidth": 2000,
                "normalizedImageMaxHeight": 2000
            },
            "context": "/document",
            "inputs": [{"name": "file_data", "source": "/document/file_data"}],
            "outputs": [
                {"name": "content", "targetName": "extracted_content"},
                {"name": "normalized_images", "targetName": "normalized_images"}
            ]
        },
        {
            "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
            "name": "split-skill",
            "description": "Chunk extracted text",
            "context": "/document",
            "defaultLanguageCode": "en",
            "textSplitMode": "pages",
            "maximumPageLength": 2000,
            "pageOverlapLength": 200,
            "unit": "characters",
            "inputs": [{"name": "text", "source": "/document/extracted_content"}],
            "outputs": [{"name": "textItems", "targetName": "pages"}]
        },
        {
            "@odata.type": "#Microsoft.Skills.Vision.VectorizeSkill",
            "name": "text-embedding-skill",
            "description": "Multimodal embeddings for text chunks",
            "context": "/document/pages/*",
            "modelVersion": MODEL_VERSION,
            "inputs": [{"name": "text", "source": "/document/pages/*"}],
            "outputs": [{"name": "vector", "targetName": "text_vector"}]
        },
        {
            "@odata.type": "#Microsoft.Skills.Vision.VectorizeSkill",
            "name": "image-embedding-skill",
            "description": "Multimodal embeddings for extracted images",
            "context": "/document/normalized_images/*",
            "modelVersion": MODEL_VERSION,
            "inputs": [{"name": "image", "source": "/document/normalized_images/*"}],
            "outputs": [{"name": "vector", "targetName": "image_vector"}]
        },
        {
            "@odata.type": "#Microsoft.Skills.Util.ShaperSkill",
            "name": "shaper-skill",
            "description": "Reshape image metadata and build content_path",
            "context": "/document/normalized_images/*",
            "inputs": [
                {"name": "normalized_images", "source": "/document/normalized_images/*"},
                {
                    "name": "imagePath",
                    "source": f"='{IMAGE_PROJECTION_CONTAINER}/'+$(/document/normalized_images/*/imagePath)"
                },
                {
                    "name": "location_metadata",
                    "sourceContext": "/document/normalized_images/*",
                    "inputs": [
                        {"name": "page_number", "source": "/document/normalized_images/*/pageNumber"},
                        {"name": "bounding_polygons", "source": "/document/normalized_images/*/boundingPolygon"}
                    ]
                }
            ],
            "outputs": [{"name": "output", "targetName": "new_normalized_images"}]
        }
    ],
    "cognitiveServices": {
        "@odata.type": "#Microsoft.Azure.Search.AIServicesByIdentity",
        "subdomainUrl": COGNITIVE_SERVICES_URL,
        "identity": None
    },
    "indexProjections": {
        "selectors": [
            {
                "targetIndexName": INDEX_NAME,
                "parentKeyFieldName": "text_document_id",
                "sourceContext": "/document/pages/*",
                "mappings": [
                    {"name": "content_embedding", "source": "/document/pages/*/text_vector"},
                    {"name": "content_text", "source": "/document/pages/*"},
                    {"name": "document_title", "source": "/document/document_title"}
                ]
            },
            {
                "targetIndexName": INDEX_NAME,
                "parentKeyFieldName": "image_document_id",
                "sourceContext": "/document/normalized_images/*",
                "mappings": [
                    {"name": "content_embedding", "source": "/document/normalized_images/*/image_vector"},
                    {"name": "content_path", "source": "/document/normalized_images/*/new_normalized_images/imagePath"},
                    {"name": "location_metadata", "source": "/document/normalized_images/*/new_normalized_images/location_metadata"},
                    {"name": "document_title", "source": "/document/document_title"}
                ]
            }
        ],
        "parameters": {"projectionMode": "skipIndexingParentDocuments"}
    },
    "knowledgeStore": {
        "storageConnectionString": STORAGE_RESOURCE_ID,
        "identity": None,
        "projections": [
            {
                "files": [
                    {
                        "storageContainer": IMAGE_PROJECTION_CONTAINER,
                        "source": "/document/normalized_images/*"
                    }
                ]
            }
        ]
    }
}

# ----------------------------
# 4) Indexer (connect ds + skillset + index)
# DOCX title mapping uses metadata_storage_name
# ----------------------------
indexer = {
    "name": INDEXER_NAME,
    "dataSourceName": DATASOURCE_NAME,
    "targetIndexName": INDEX_NAME,
    "skillsetName": SKILLSET_NAME,
    "parameters": {
        "maxFailedItems": -1,
        "maxFailedItemsPerBatch": 0,
        "batchSize": 1,
        "configuration": {
            "allowSkillsetToReadFileData": True
        }
    },
    "fieldMappings": [
        {"sourceFieldName": "metadata_storage_name", "targetFieldName": "document_title"}
    ]
}

def main():
    print("Creating datasource...")
    put(f"/datasources/{DATASOURCE_NAME}", datasource)

    print("Creating index...")
    put(f"/indexes/{INDEX_NAME}", index)

    print("Creating skillset...")
    put(f"/skillsets/{SKILLSET_NAME}", skillset)

    print("Creating indexer...")
    put(f"/indexers/{INDEXER_NAME}", indexer)

    print("Running indexer...")
    post(f"/indexers/{INDEXER_NAME}/run")

    print("Check status:")
    status = get(f"/indexers/{INDEXER_NAME}/status")
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()