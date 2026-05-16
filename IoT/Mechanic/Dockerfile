FROM espressif/idf:v6.0.1

# Install both QEMU architectures
RUN apt-get update && apt-get install -y libgcrypt20 libglib2.0-0 libpixman-1-0 libsdl2-2.0-0 libslirp0\
    && python3 $IDF_PATH/tools/idf_tools.py install qemu-xtensa \
    && python3 $IDF_PATH/tools/idf_tools.py install qemu-riscv32 \
    && python3 $IDF_PATH/tools/idf_tools.py install-python-env

# Add BOTH to the system path
# Note: The specific date/version strings in the path may change with IDF updates
ENV PATH="/root/.espressif/tools/qemu-xtensa/esp-develop-20220919-v4.2.0/qemu/bin:/root/.espressif/tools/qemu-riscv32/esp-develop-20220919-v4.2.0/qemu/bin:${PATH}"
ENV IDF_TARGET=esp32s3
WORKDIR /project

COPY . .

# Disable PHY calibration and data storage to avoid issues in QEMU
RUN echo "CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=n" >> sdkconfig.defaults
RUN echo "CONFIG_ESP_PHY_INIT_DATA_IN_PARTITION=n" >> sdkconfig.defaults

ARG MQTT_HOST=""
ARG MQTT_PORT=""
ARG MQTT_USER=""
ARG MQTT_PASSWORD=""

# Construct the MQTT URI and append it to sdkconfig.defaults only if MQTT_HOST is provided
RUN if [ -n "$MQTT_HOST" ]; then \
      if [ -n "$MQTT_USER" ]; then \
        echo "CONFIG_MQTT_DEFAULT_BROKER_URI=\"mqtt://${MQTT_USER}:${MQTT_PASSWORD}@${MQTT_HOST}:${MQTT_PORT}\"" >> sdkconfig.defaults; \
      else \
        echo "CONFIG_MQTT_DEFAULT_BROKER_URI=\"mqtt://${MQTT_HOST}:${MQTT_PORT}\"" >> sdkconfig.defaults; \
      fi; \
    fi

#build the project
RUN /bin/bash -c "source $IDF_PATH/export.sh && idf.py build"

CMD ["/bin/bash", "-c", "source $IDF_PATH/export.sh && idf.py qemu --qemu-extra-args='-nic user,model=open_eth,hostfwd=tcp::5001-:80 -object can-bus,id=canbus0 -object can-host-socketcan,id=canhost0,if=vcan0,canbus=canbus0 -global esp32s3-twai.canbus=canbus0' monitor"]