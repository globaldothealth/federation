# Partner edge system

This folder contains an emulated partner service, along with dependencies, run inside a `docker-compose` stack.

While it does not precisely represent a real-world deployment, it does accurately show how requests and responses work with the Global.health cloud system. We assume use of PostGREs database and Global.health day zero schema here; in reality the partner will use their own and the Global.health team will work with them to build a database connection function and adaptors between schemas. This emulated partner does not show the update process either, we put that in another folder.
