# Remote dependency management

This folder contains a information about how Global.health (G.h) and partners incorporate new analysis scripts into their systems. It also includes a proof of concept for this (roughly outlined) process:

- The G.h team evaluates a candidate script
- At least one partner agrees to run it
- The G.h team creates a new build for its service
- The G.h team deploys the build
- The G.h team creates a new build for the relevant partner(s)
- The partner daemon(s) deploy the new build


## Instructions for researchers (those submitting a candidate script)


The G.h federated system can incorporate new Python scripts for partners to run and provide new data insights, while keeping their data private.

To add a Python script to the system, one should share relevant code with a G.h team member, and include as much of the following as possible:

- a brief description of what the script does
- target data sets (i.e. which pathogens)
- what work partner services should perform
- what work Global.health services should perform
- expected output
- instructions to run
- dependency management (library versions)
- how data relates to G.h schema (i.e. how to get one from the other)

Before running the script, the Global.health team will ensure it works as described, and that no dependency conflicts exist between it and the federated system.
The team will then ensure tests exist, and automate them in a CI/CD pipeline.
The team will then consult with relevant partners, inviting them to opt into running the new script on their systems.
For partners who agree, the Global.health team will publish new Docker images containing required updates, and those partners will receive automatic updates when their services become idle. 

Development effort from the Global.health team depends on the state of the script and desired behaviors. Following good practices for writing code like meaningful names and SOLID helps!


## Instructions for developers


The G.h team maintains Docker images for each partner, as each brings different technical needs some may participate in analyses others do not.

Before a new script is added to the federated system, it must be included in the suite of integration and end-to-end tests to prove that it works as expected and catch conflicts or defects introduced by future work, including additional scripts.

The G.h server images will require updates; these happen on a rolling basis with no downtime and blue/green deployments (TODO: confirm) through Kubernetes. At least, new .protobuf files and code for requests and responses for that new script will be needed, and generated `_pb2` Python files.  The deployments should occur before updating the partner image.

When a partner opts into running a new script, a developer needs to create a new image for that partner and push it to the repository (ECR) when the partner wants to start using it. The code used for new images must pass automated tests, including new ones for that script and its outputs.

The update process should occur automatically: partner systems run a daemon service that regularly checks the image repository for updates and applies them (pulling the new image, stopping the old container, and starting a new container) when the partner gRPC service idles. The partner should provide a desired window of time for updates, and Global.health should advertise downtime in advance.


## Testing


The test for updating a partner image follows a standard "arrange, act, assert" pattern.

Arrange:
A shell script starts Localstack, an AMQP server, setup scripts, and a daemon script.
The setup scripts create the ECR image repository and push two semver-tagged partner service images to it.
The shell script then starts the partner service container labeled with the older version tag.
The test gets the image version tags from the iamge repository and the version label from the running service container.
The test determines readiness from a status endpoint in the service container.

Act:
The daemon script requests the partner service's state via HTTP endpoint. The service indicates an idle state.
The daemon script gets the updated version tag from the image repository.
The daemon script pulls the new image and restarts the container, passing in the new version tag as a container label.

Assert:
The test gets the image version tag from the repository and running service container.
The version tag should be the highest, and should match the container's version label.
