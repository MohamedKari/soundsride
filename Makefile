conda-env:
	conda env update -f env.yml

conda-env-file:
	conda env export | grep -v "^prefix: "

show-outdated:
	pip list --outdated

install-editable:
	pip install -e .

.PHONY: tests
tests: conda-env install-editable
	pytest

python-protos:
	python -m grpc_tools.protoc \
		-I grpc \
		--python_out=. \
		--grpc_python_out=. \
		grpc/soundsride/service/*.proto

	touch soundsride/service/__init__.py