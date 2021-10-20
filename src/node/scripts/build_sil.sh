mkdir -p build_sil
g++ -Ofast -DMULTI_RHNODE_MAX=$1 *.cpp sil/*.cpp -Isil -o build_sil/rhnode$1
