FROM ubuntu:latest
ENV DEBIAN_FRONTEND noninteractive
WORKDIR /code
RUN apt-get update && apt-get -y upgrade && apt-get -y install nano python3 python3-pip libgdal-dev fftw3-dev r-base
COPY docker/install_r_packages.R .
RUN Rscript install_r_packages.R
COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN pip3 install uwsgi
COPY specgen ./specgen
COPY specweb ./specweb
COPY *.py .
RUN python3 gen_config.py
RUN echo "The enviroment has been set up, but you still need to edit"
RUN echo "the /code/specgen/config.ini file as needed, and then"
RUN echo "edit and run gen_station_config.py before things will work"
CMD python3 run_web.py