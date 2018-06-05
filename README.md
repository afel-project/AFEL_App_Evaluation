# AFEL App Evaluation Analysis
Contributors: Rémi Venant, Sana Syeda, Mathieu d'Aquin (@mdaquin)

This repository provides:

- the application 'afelTraces2rdf' to transform the heterogenous log files of the 2nd evaluation into a unique consistant RDF file, 
- a docker-compose file to launch a Jena-Fuseki container, 
- and the different jupyter files of the analysis.

## 1. Requirements
The afelTraces2rdf application relies on the following softwares:

- python >= 3.6
- pip

The required packages for the application are listed in the requirements.txt file located in the application folder.
An automatic installation of the packages can be achieved by the following command, to execute within the repository folder:
	pip install -r afelTraces2rdf/requirements.txt
Working with a virtual environment is recommended.

The Jena-Fuseki docker-compose file relies on the following softwares:

- docker
- docker-compose >= 3.2 (usually shipped with docker)

## 2. Repository structure
This respository is structed as follow:

- afelTraces2rdf: the python application sources
- resources: contains raw traces, the RDF AFEL vocabulary extension and the different RDF models schema
- docker-compose.yml: the docker-compose file to manage the Jena-Fuseki server
- requirements.txt: the python package requirement for the afelTraces2rdf application
- README.md: this file

## 3. General Information

### 3.1. RDF Namespaces
The data relies on the 3 specific namespaces:

- [http://vocab.afel-project.eu/](http://data.afel-project.eu/vocab/afel_schema.rdf)
- http://vocab.afel-project.eu/extension/ (available in the repository in the resources folder)
- [http://schema.org/](http://schema.org/)

### 3.2 RDF Models
The models of the definitions used in the traces can be found in the resources/schema model.

## 4. RDF File creation with afelTraces2rdf
The afelTraces2rdf application can be launched from a terminal. Inside the repository folder, one can run the following command:
	python -m afelTraces2rdf.migrator path/to/my_outputfile.ttl
The different options proposed by the application can be obtain using the --help parameter.

## 5. Jena-Fuseki server management
The server relies on docker-compose. To launch it, execute the following command in a terminal, within the repository folder:
	docker-compose up
To shut down the container, execute the following command from the same folder:
	docker-compose down

### 5.1. Setting up the Jena-Fuseki server
The container is configured to manage persistence across different runs of the container. However, it needs to be populate with the generated RDF file generated previously.
Once the server is launcher, it can be accessed with a browser using the url http://localhost:3030.
Follow the several steps:

1. Go to manage datasets.
1. Choose add new dataset
1. Choose a name and set its type as persistent
1. Once created, choose "upload data"
1. leave  the destination graph name empty
1. select the file previously generated

### 5.2. Clear the Jena-Fuseki contained
Once down, a docker volume is kept for persitence management. To remove it, execute the followin command:
    docker volume rm afel_evaluation2_fusekidata

### 5.3 Sample of a SPARQL query on the data
The following request lists all urls of artifacts viewed by the user 'project.afel+002'

	PREFIX afl: <http://vocab.afel-project.eu/>

	SELECT ?date ?url
	WHERE { $aView  afl:user  $user .
	  $aView a afl:ArtifactView .
	  $user afl:person $pers .
	  $pers afl:firstName "project.afel+002" .
	  $aView afl:artifact $artifact .
	  $artifact afl:URL ?url .
	  $aView afl:eventStartDate ?date .
	}

## 6. Licence 
The AFEL Chrome Browsing History Extension us distributed under the [Apache Licence V2](https://www.apache.org/licenses/LICENSE-2.0). Please attribute Rémi Venant, Sana Syeda and [Mathieu d'Aquin](http://mdaquin.net)  through the [AFEL Project](http://afel-project.eu)* when reusing and redistributing this code.




