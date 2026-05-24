FROM espressif/idf:v6.0.1 AS base

# Install QEMU + dependencies
RUN apt-get update && apt-get install -y \
    libgcrypt20 \
    libglib2.0-0 \
    libpixman-1-0 \
    libsdl2-2.0-0 \
    libslirp0 \
    && python3 $IDF_PATH/tools/idf_tools.py install qemu-xtensa \
    && python3 $IDF_PATH/tools/idf_tools.py install qemu-riscv32 \
    && python3 $IDF_PATH/tools/idf_tools.py install-python-env

# QEMU binaries
ENV PATH="/root/.espressif/tools/qemu-xtensa/esp_develop_9.2.2_20250817/qemu/bin:/root/.espressif/tools/qemu-riscv32/esp_develop_9.2.2_20250817/qemu/bin:${PATH}"

ENV IDF_TARGET=esp32s3

WORKDIR /project

FROM base AS deps

COPY CMakeLists.txt sdkconfig.defaults ./
COPY main/ ./main/
COPY components/ ./components/

ARG MQTT_HOST=""
ARG MQTT_PORT=""
ARG MQTT_USER=""
ARG MQTT_PASSWORD=""

RUN touch sdkconfig.defaults \
    && sed -i '/^CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=/d' sdkconfig.defaults \
    && sed -i '/^CONFIG_ESP_PHY_INIT_DATA_IN_PARTITION=/d' sdkconfig.defaults \
    && echo "CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=n" >> sdkconfig.defaults \
    && echo "CONFIG_ESP_PHY_INIT_DATA_IN_PARTITION=n" >> sdkconfig.defaults \
    && echo "CONFIG_DTC_POLL_INTERVAL_MINUTES=1" >> sdkconfig.defaults

RUN if [ -n "$MQTT_HOST" ]; then \
      sed -i '/^CONFIG_MQTT_DEFAULT_BROKER_URI=/d' sdkconfig.defaults; \
      if [ -n "$MQTT_USER" ]; then \
        echo "CONFIG_MQTT_DEFAULT_BROKER_URI=\"mqtt://${MQTT_USER}:${MQTT_PASSWORD}@${MQTT_HOST}:${MQTT_PORT}\"" >> sdkconfig.defaults; \
      else \
        echo "CONFIG_MQTT_DEFAULT_BROKER_URI=\"mqtt://${MQTT_HOST}:${MQTT_PORT}\"" >> sdkconfig.defaults; \
      fi; \
    fi

RUN --mount=type=cache,target=/root/.espressif,id=espressif-tools \
    --mount=type=cache,target=/project/build,id=idf-build \
    /bin/bash -c "source $IDF_PATH/export.sh && idf.py reconfigure"

FROM base AS build

COPY . .
COPY --from=deps /project/sdkconfig.defaults /project/sdkconfig.defaults
COPY --from=deps /project/managed_components /project/managed_components

RUN --mount=type=cache,target=/root/.espressif,id=espressif-tools \
    --mount=type=cache,target=/project/build,id=idf-build \
    /bin/bash -c "source $IDF_PATH/export.sh && idf.py build"

CMD ["/bin/bash", "-c", "source $IDF_PATH/export.sh && idf.py qemu --qemu-extra-args='-nic user,model=open_eth,hostfwd=tcp::5001-:80 -object can-bus,id=canbus0 -object can-host-socketcan,id=canhost0,if=vcan0,canbus=canbus0 -global driver=esp32s3.twai,property=canbus,value=canbus0 -trace \"can_*\" -trace \"sja1000_*\"' monitor 2>&1 | tee -a /project/qemu.log"]