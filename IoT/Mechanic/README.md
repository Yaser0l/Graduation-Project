## How to Add a Quick Env source

```
echo 'alias get_idf="source /home/azoz-laptop/.espressif/tools/activate_idf_v6.0.1.sh"' >> ~/.bashrc
```

## How to Add Dependancies

```sh
get_idf
idf.py add-dependency "namespace/component^version"
```

## How to Build

```sh
get_idf
idf.py fullclean
idf.py build
```

## How to Unit Test

```
./scripts/converage_local.sh
```
