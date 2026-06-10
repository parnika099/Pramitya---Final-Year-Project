<div align="center" markdown="1">

<img src="docs/images/lms-logo.png" alt="Pramitya logo" width="80" height="80"/>
<h1>Pramitya</h1>

**Open source learning management system with AI viva assessments**

![Tests](https://img.shields.io/endpoint?url=https://dashboard.cypress.io/badge/simple/vandxn/main&style=flat&logo=cypress)

</div>


<div align="center">
	<img src="docs/images/hero.png?v=5" alt="Hero Image" width="72%" />
</div>
<br />
<div align="center">
	<a href="/lms">Website</a>
	-
	<a href="/lms">Documentation</a>
</div>

## Pramitya
Pramitya is an easy-to-use learning system that helps you bring structure to your content and assess learners with AI viva sessions.

### Motivation
In 2021, we were looking for a Learning Management System to launch [Mon.School](https://mon.school) for FOSS United. We checked out Moodle, but it didn’t feel right. The forms were unnecessarily lengthy and the UI was confusing. It shouldn't be this hard to create a course right? So I started making a learning system for Mon.School which soon became a product in itself. The aim is to have a simple platform that anyone can use to launch a course of their own and make knowledge sharing easier.

### Key Features

- **Structured Learning**: Design a course with a 3-level hierarchy, where your courses have chapters and you can group your lessons within these chapters. This ensures that the context of the lesson is set by the chapter.

- **Live Classes**: Group learners into batches based on courses and duration. You can then create Zoom live class for these batches right from the app. Learners get to see the list of live classes they have to take as a part of this batch.

- **Quizzes and Assignments**: Create quizzes where questions can have single-choice, multiple-choice options, or can be open ended. Instructors can also add assignments which learners can submit as PDF's or Documents.

- **Getting Certified**: Once a learner has completed the course or batch, you can grant them a certificate. The app provides an inbuilt certificate template. You can use this or else create a template of your own and use that instead.

<details>
<summary>View Screenshots</summary>


![Batch](docs/images/batch.png)
<div align="center">
	<sub>
		Create batches to group your learners
	</sub>
</div>
<br>


![Quiz](docs/images/quiz.png)
<div align="center">
	<sub>
		Evaluate their knowledge by quizzes
	</sub>
</div>
<br>


![Cerficicate](docs/images/certificate.png)
<div align="center">
	<sub>
		Autenticate their work with certification
	</sub>
</div>
</details>


### Under the Hood

- [**Frappe Framework**](https://github.com/frappe/frappe): A full-stack web application framework.

- [**Frappe UI**](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface.

## Production Setup

### Azure Single-VM Deployment

The Pramitya deployment path in this repository provisions a small Azure VM, uploads the current source tree, and starts Docker Compose with MariaDB, Redis, Frappe bench, and Caddy.

```bash
./scripts/deploy-pramitya-azure.sh
```

Optional environment variables:

```bash
AZURE_LOCATION=centralindia
AZURE_VM_SIZE=Standard_B1ms
AZURE_DNS_LABEL=pramitya
PRAMITYA_DOMAIN=example.com
```

When `PRAMITYA_DOMAIN` is set, the script creates an Azure DNS zone and an A record for `pramitya.example.com`. Delegate the domain to the Azure nameservers printed by the script.

## Development Setup

### Docker

You need Docker, docker-compose and git setup on your machine. Refer [Docker documentation](https://docs.docker.com/). After that, follow below steps:

**Step 1**: Setup folder and download the required files

    mkdir pramitya
    cd pramitya

    # Download the docker-compose file
    cp /path/to/repo/docker/docker-compose.yml docker-compose.yml

    # Download the setup script
    cp /path/to/repo/docker/init.sh init.sh

**Step 2**: Run the container and daemonize it

    docker compose up -d

**Step 3**: The site [http://lms.localhost:8000/lms](http://lms.localhost:8000/lms) should now be available. The default credentials are:
- Username: Administrator
- Password: admin

### Local

To setup the repository locally follow the steps mentioned below:

1. Install bench and setup a `frappe-bench` directory by following the [Installation Steps](https://frappeframework.com/docs/user/en/installation)
1. Start the server by running `bench start`
1. In a separate terminal window, create a new site by running `bench new-site learning.test`
1. Map your site to localhost with the command `bench --site learning.test add-to-hosts`
1. Get the Pramitya app from this repository.
1. Run `bench --site learning.test install-app lms`.
1. Now open the URL `http://learning.test:8000/lms` in your browser, you should see the app running

## Learn and connect

- [Frappe Framework](https://frappeframework.com/docs)

<br>
<br>
<div align="center" style="padding-top: 0.75rem;">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
