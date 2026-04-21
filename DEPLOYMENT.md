# Deployment Guide

This is a guide for how to deploy the web interface, database, and document scraper.

### Requirements
 - [Docker](https://docs.docker.com/desktop/setup/install/linux/)
 - Any Linux distribution which supports Docker.  The guide is written for Linux, but similar steps can be taken on other platforms such as Windows.

### Building

First, the Docker image for the web interface must be built.

```
cd [PATH TO GIT REPO]
docker build -t seagrant .
```

Next, the container for the image must be created.  Here, we expose port 8501 to the host to allow access to the web interface.

```
docker container create -p 8501:8501 --name seagrant-website seagrant
```

Note the string of characters outputted by the above command.  This is the ID of the
docker container, which we will need to start and stop the container.  After creation, you can find
the ID again with the following command:

```
docker container ls -a | grep seagrant-website
```

The first string of random numbers and characters is the ID.

### Running

To start the container, type the following command:

```
docker container start [CONTAINER ID]
```

You should now be able to access the web interface in a web browser on `localhost:8501`.
If not, verify the docker container started correctly.

To stop the container, type the following command:

```
docker container stop [CONTAINER ID]
```

