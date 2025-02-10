import json
w = """
{
    "llm_list": {
        "local2": {
            "BaseURL": "http://localhost:1234/v1",
            "ApiKey": "none",
            "BatchSize": 10,
            "ThreadNum": 10
        }
    },
    "model_list": {}
}
"""

data = json.loads(w)
print( data["llm_list"]["local2"] )
