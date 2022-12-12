
A simple demo, how SAPL can be used to secure a Flask Application.

There are 3 endpoints for POST requests and the authentication is made with a JWT.

## How to install

- Clone the project and install the dependencies from the pyproject.toml file
- Download and run a PDP Server
- Copy the policy files, which are included in the project to the folder which is mounted to the PDP Server

## Set up the PDP Server

The project needs a PDP Server to work. Explanation on how to create a PDP Server can be found in the [SAPL 
GitHub repository](https://github.com/heutelbeck/sapl-policy-engine/tree/master/sapl-server-lt)

## Configure the PDP Server

To connect to the PDP Server, the connection needs to be configured. The default configuration assumes, that a 
SAPL-Server-lt is running in a docker container on localhost:8080. Different Configurations can be used by setting the 
appropriate variables in the config.json file.

An example for a configuration with the default values could be:
{
  "POLICY_DECISION_POINT" : {
    "dummy": false,
    "base_url": "http://localhost:8080/api/pdp/",
    "key": "YJidgyT2mfdkbmL",
    "secret": "Fa4zvYQdiwHZVXh",
    "verify": false
  }
}

The following list contains customizable variables for the configuration

- "base_url"
- "key"
- "secret"
- "verify"
- "dummy"


### Endpoints

The project has 3 endpoints, which are all accessible with POST requests. Each Request has to be made with a JWT as 
authentication. The endpoints are:

- /pre_enforce/POST/<int:data_id>
- /post_enforce/POST
- /pre_and_post_enforce/POST/<int:data_id>

### Tokens to authenticate

Each endpoint has policies for 2 different users, access from anyone else is denied by default.
For the 2 user you can use these tokens, which use the algorithm HS256 and contain their name as payload:

- The user 'John' has the Token: 
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiSm9obiJ9.V0tldsLafETWh4JaAEig0BA2oqAZcbb9w55tGRLJRHs
- The user 'Julia' has the Token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiSnVsaWEifQ.oRaEyZ_pZeKudooNO5KgSiqwI5UwD5zk-nfCnnuWnlw
