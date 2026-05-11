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

CMD ["sh", "-c", "idf.py qemu monitor"]