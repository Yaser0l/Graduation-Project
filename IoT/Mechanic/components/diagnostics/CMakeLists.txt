idf_component_register(
    SRCS 
        "dtc_reporter.c"
    PRIV_REQUIRES
        "esp_driver_twai"
        "vehicle_comms"
)