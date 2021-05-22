mkdir -p build_ci
g++ -g -O0 --coverage -DMULTI_RHNODE_MAX=$1 *.cpp sil/*.cpp -o build_ci/rhnode$1
