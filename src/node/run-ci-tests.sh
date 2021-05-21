for f in test/*.cpp;
do
	test_name=$(basename "$f")
	cov_dir=$(basename "$f" .cpp)
	echo Testing $f
	bundle exec arduino_ci.rb --skip-examples-compilation --testfile-select=$test_name
	gcov -b -c *.cpp
	mkdir $cov_dir
	mv *.gcov $cov_dir
	rm *.gcda
	rm *.gcno
done
