FROM pypy:2
RUN apt-get update
RUN apt-get install -y libxml2 libxml2-dev libxslt-dev pypy-dev
RUN apt-get install -y git
RUN pip install -e git+git://github.com/aglyzov/lxml.git@cffi#egg=lxml-cffi
RUN pip install databaker
RUN mkdir -p /demo
COPY . /demo

ENTRYPOINT /bin/bash
