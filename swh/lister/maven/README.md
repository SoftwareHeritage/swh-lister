
## The Maven lister

This readme describes the design decisions made during development.

More information can be found on the Software Heritage forge at [https://forge.softwareheritage.org/T1724](https://forge.softwareheritage.org/T1724) and on the diff of the lister at [https://forge.softwareheritage.org/D6133](https://forge.softwareheritage.org/D6133) .

## Execution sequence (TL;DR)

The complete sequence of actions to list the source artifacts and scm urls is as follows:

On the `index_exporter` server (asynchronously):

* Check the list of remote indexes, and compare it to the list of local index files.
* Retrieve the missing Maven Indexer indexes from the remote repository. \
  Example of index from Maven Central: [https://repo1.maven.org/maven2/.index/](https://repo1.maven.org/maven2/.index/)
* Start execution of the Docker container:
  * If the `indexes` directory doesn't exist, unpack the Lucene indexes from the Maven Indexer indexes using `indexer-cli`.\
    This generates a set of binary files as shown below:

    ```
    boris@castalia:maven$ ls -lh /media/home2/work/indexes/
    total 5,2G
    -rw-r--r-- 1 root root 500M juil.  7 22:06 _4m.fdt
    -rw-r--r-- 1 root root 339K juil.  7 22:06 _4m.fdx
    -rw-r--r-- 1 root root 2,2K juil.  7 22:07 _4m.fnm
    -rw-r--r-- 1 root root 166M juil.  7 22:07 _4m_Lucene50_0.doc
    -rw-r--r-- 1 root root 147M juil.  7 22:07 _4m_Lucene50_0.pos
    -rw-r--r-- 1 root root 290M juil.  7 22:07 _4m_Lucene50_0.time
    -rw-r--r-- 1 root root 3,1M juil.  7 22:07 _4m_Lucene50_0.tip
    [SNIP]
    -rw-r--r-- 1 root root  363 juil.  7 22:06 _e0.si
    -rw-r--r-- 1 root root 1,7K juil.  7 22:07 segments_2
    -rw-r--r-- 1 root root    8 juil.  7 21:54 timestamp
    -rw-r--r-- 1 root root    0 juil.  7 21:54 write.lock
    ```
  * If the `export` directory doesn't exist, export the Lucene documents from the Lucene indexes using `clue`.\
    This generates a set of text files as shown below:

    ```
    boris@castalia:~$ ls -lh /work/export/
    total 49G
    -rw-r--r-- 1 root root  13G juil.  7 22:12 _p.fld
    -rw-r--r-- 1 root root 7,0K juil.  7 22:21 _p.inf
    -rw-r--r-- 1 root root 2,9G juil.  7 22:21 _p.len
    -rw-r--r-- 1 root root  33G juil.  7 22:20 _p.pst
    -rw-r--r-- 1 root root  799 juil.  7 22:21 _p.si
    -rw-r--r-- 1 root root  138 juil.  7 22:21 segments_1
    -rw-r--r-- 1 root root    0 juil.  7 22:07 write.lock
    ```
* On the host, copy export files  to `/var/www/html/` to make them available on the network.

On the lister side:

* Get the exports from the above local index server.
* Extract the list of all pom and source artefacts from the Lucene export.
* Yield the list of source artefacts to the Maven Loader as they are found.
* Download all poms from the above list.
* Parse all poms to extract the scm attribute, and yield the list of scm urls towards the classic loaders (git, svn, hg..).

The process has been optimised as much as it could be, scaling down from 140 GB on disk / 60 GB RAM / 90 mn exec time to 60 GB on disk / 2 GB (excl. docker) / 32 mn exec time.

For the long read about why we came to here, please continue.

## About the Maven ecosystem

Maven repositories are a loose, decentralised network of HTTP servers with a well-defined hosted structure. They are used according to the Maven dependency resolver[i](#sdendnote1sym), an inheritance-based mechanism used to identify and locate artefacts required in Maven builds.

There is no uniform, standardised way to list the contents of maven repositories, since consumers are supposed to know what artefacts they need. Instead, Maven repository owners usually setup a Maven Indexer[ii](#sdendnote2sym) to enablesource code identification and listing in IDEs – for this reason, source jars usually don’t have build files and information, only providing pure sources.

Maven Indexer is not a mandatory part of the maven repository stack, but it is the *de facto* standard for maven repositories indexing and querying. All major Maven repositories we have seen so far use it. Most artefacts are located in the main central repository: Maven Central[iii](#sdendnote3sym), hosted and run by Sonatype[iv](#sdendnote4sym). Other well-known repositories are listed on MVN Repository[v](#sdendnote5sym).

Maven repositories are mainly used for binary content (e.g. class jars), but the following sources of information are relevant to our goal in the maven repositories/ecosystem:

* SCM attributes in pom XML files contain the **scm URL** of the associated source code. They can be fed to standard Git/SVN/others loaders.
* **Source artefacts** contain pure source code (i.e. no build files) associated to the artefact. There are two main naming conventions for them, although not always enforced:
  * ${artifactId}-${version}-source-release.zip
  * ${artifactId}-${version}-src.zip

  They come in various archiving formats (jar, zip, tar.bz2, tar.gz) and require a specific loader to attach the artefact metadata.

[i](#sdendnote1anc)Maven dependency resolver: [https://maven.apache.org/resolver/index.html](https://maven.apache.org/resolver/index.html)

[ii](#sdendnote2anc)Maven Indexer: [https://maven.apache.org/maven-indexer/](https://maven.apache.org/maven-indexer/)

[iii](#sdendnote3anc)Maven Central: [https://search.maven.org/](https://search.maven.org/)

[iv](#sdendnote4anc)Sonatype Company: [https://www.sonatype.com/](https://www.sonatype.com/)

[v](#sdendnote5anc)MVN Repository: [https://mvnrepository.com/repos](https://mvnrepository.com/repos)

## Preliminary research

Listing the full content of a Maven repository is very unusual, and the whole system has not been built for this purpose. Instead, tools and build systems can easily fetch individual artefacts according to their Maven coordinates (groupId, artifactId, version, classifier, extension). Usual listing means (e.g. scapping) are highly discouraged and will trigger bannishment easily. There is no common API defined either.

Once we have the artifactId/group we can easily get the list of versions (e.g. for updates) by reading the [maven-metadata.xml file at the package level](https://repo1.maven.org/maven2/ant/ant/maven-metadata.xml), although this is not always reliable. The various options that were investigated to get the interesting artefacts are:

* **Scrapping** could work but is explicitly forbidden[i](#sdendnote1sym). Pages could easily be parsed through, and it would allow to identify \*all\* artifacts.
* Using **Maven indexes** is the "official" way to retrieve information from a maven repository and most repositories provide this feature. It would also enable a smart incremental listing. The Maven Indexer data format however is not we
  ll documented. It relies under the hood on an old version (Lucene54) of a lucene indexes, and the only libraries that can access it are written in java. This implies a dedicated Docker container with a jvm and some specific tools (maven indexer and luke for the lucene index), and thus would bring some complexity to the docker & prod setups.
* A third path could be to **parse all the pom.xml's** that we find and follow all artifactId's recursively, building a graph of dependencies and parent poms. This is more of a non-complete heuristic, and we would miss leaf nodes (i.e. artifacts that are not used by others), but it could help setup a basic list.
* It should be noted also that there are two main implementations of maven repositories: Nexus and Artifactory. By being more specific we could use the respective APIs of these products to get information. But getting the full list of artefacts is still not straightforward, and we'd lose any generic treatment doing so.

The best option in our opinion is to go with the Maven Indexer, for it is the most complete listing available (notably for the biggest repository by far: maven central).

[i](#sdendnote1anc)Maven repository’s Terms of Service: [https://repo1.maven.org/terms.html](https://repo1.maven.org/terms.html)

## Maven indexes conversion

[Maven-Indexer](https://maven.apache.org/maven-indexer/) is a (thick) wrapper around lucene. It parses the repository and stores documents, fields and terms in an index. One can extract the lucene index from a maven index using the command: `java -jar indexer-cli-5.1.1.jar --unpack nexus-maven-repository-index.gz --destination test --type full`. Note however that 5.1.1 is an old version of maven indexer; newer versions of the maven indexer won't work on the central indexes.

[Clue](https://maven.apache.org/maven-indexer/) is a CLI tool to read lucene indexes, and version 6.2.0 works with our maven indexes. One can use the following command to export the index to text: `java -jar clue-6.2.0-1.0.0.jar maven/central-lucene-index/ export central_export text`.

The exported text file looks like this:

```
doc 0
  field 0
    name u
    type string
    value com.redhat.rhevm.api|rhevm-api-powershell-jaxrs|1.0-rc1.16|javadoc|jar
  field 1
    name m
    type string
    value 1321264789727
  field 2
    name i
    type string
    value jar|1320743675000|768291|2|2|1|jar
  field 10
    name n
    type string
    value RHEV-M API Powershell Wrapper Implementation JAX-RS
  field 13
    name 1
    type string
    value 454eb6762e5bb14a75a21ae611ce2048dd548550
```

The execution of these two jars requires a Java virtual machine -- java execution in python is not possible without a JVM. Docker is a good way to run both tools and generate the exports independently, rather than add a JVM to the existing production environment.

We decided (2021-08-25) to install and execute a docker container on a separate server so the lister would simply have to fetch it on the network and parse it (the latter part in pure python).
