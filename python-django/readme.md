# Flagsmith Django Test

## Requirements

We'd like you to develop a basic feature flagging API. The API should consist of a single endpoint to return a list of
flags for a given environment. The models you should need are Feature, Environment and Flag. The Feature and Environment
models should just have a name (and any other metadata you may deem necessary). The Flag model should have a
relationship with the Feature and Environment, as well as a boolean value to describe whether the feature is enabled or
disabled in a given environment. The API endpoint should return the enabled / disabled state of the feature and the name
(+ metadata) for the feature. You need not return any information about the environment.

We have created the django application and some boilerplate code for you. You should complete the `flags` app in the
`apps` directory.

Some notes / clarifications:

- To determine the environment, you may use either a query parameter or an authentication class. It must not be
    possible, however, to request flags without an environment.
- You need not worry about API endpoints to manage these objects, you can use the django admin as necessary.
- You may use the default sqlite database.
- You should not implement any pagination on the list flags endpoint.

As an extension, by assuming that you will only ever have a single instance of the API application running, implement
an in-memory cache system which determines when flags were last retrieved for an environment. You should NOT use a
database field for this. You can surface this information via a new (unauthenticated) endpoint, or in the django
admin panel.

As a final extension, you are tasked with deploying this application which must be able to scale from 50 requests per
second to bursts of 2,000 requests per second. Your task is to build the platform that can serve the requests to the
API.

The priority of requirements are listed as follows with the most important first.

- Uptime/Reliability
- Low Latency
- Simplicity
- Cost

In fewer than 8 paragraphs, describe how you would achieve this. Key things to think about are: Overall design,
platform choices, any additional tools, management & maintenance.
