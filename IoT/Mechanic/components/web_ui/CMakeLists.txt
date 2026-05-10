idf_component_register(
    SRCS 
        "web_server.c"
    EMBED_TXTFILES 
        "index.html"
    PRIV_REQUIRES 
        "esp_http_server"
		"nvs_flash"
		"esp_wifi"
        "network"

)