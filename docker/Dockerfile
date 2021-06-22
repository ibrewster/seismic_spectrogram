FROM ubuntu:latest
ENV DEBIAN_FRONTEND noninteractive
WORKDIR /code
COPY requirements.txt .
COPY install_r_packages.R .
#RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 'E19F5F87128899B192B1A2C2AD5F960A256A04AF'
#RUN echo 'deb http://cloud.r-project.org/bin/linux/debian buster-cran40/' >> '/etc/apt/sources.list'

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install python3 python3-pip libgdal-dev fftw3-dev r-base
RUN Rscript install_r_packages.R
RUN pip3 install -r requirements.txt
