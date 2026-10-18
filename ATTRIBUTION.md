# Attribution

## Upstream project

Pramitya is built on top of **Frappe Learning (LMS)**, an open-source learning
management system by Frappe Technologies Pvt. Ltd. and its contributors.

- Upstream repository: https://github.com/frappe/lms
- Base version: v2.53.0 (commit `98b0fd9d`)
- Licence: GNU Affero General Public License v3.0 (see `license.txt`)

The first commit in this repository is an unmodified import of that upstream
project. Copyright in that code remains with Frappe Technologies Pvt. Ltd. and
the upstream contributors. This project is a derivative work and is distributed
under the same AGPL-3.0 licence.

## Project work

Everything after the base import was built by the Pramitya project team:

| Contributor | Area |
|---|---|
| Parnika Patil | Backend modules, data model, deployment and infrastructure |
| Shweta Mahajan | Academic records, fees, students, reporting interfaces |
| Pranita Patil | AI viva interface, course and batch experience |
| Riya Sequeira | Application shell, branding, credentialing interfaces, i18n |

Features added by this project include the AI viva examination system, verifiable
credential issuance and verification, academic records and fee management, exam
centre scheduling, role-based access control with audit logging, and the
containerised deployment stack.
