# Apple Store Scraper

A distributed web scraper for the Apple App Store. A central FastAPI server manages a URL queue and Google Cloud Spot VM workers that pull tasks, scrape app data, and discover new URLs automatically.

## Architecture

```
Server (FastAPI)
  ├── URL Queue (available → occupied → processed / terminated)
  ├── Worker Manager (spawn / delete GCP instances)
  └── Timeout Loop (detect dead VMs, requeue tasks, restart instances)

Workers (GCP Spot VMs)
  └── Poll server for tasks → scrape → extract URLs → submit results
```

Scrape workflow:

1. Initial phase starts with server having some predefined urls in server/config/initialLinks.
by default I put all groupings in there
2. After creating workers using the provided endpoints the workers set themselves up and pull the urls from the server. They then download the website and upload it to google drive. The extracted urls get sent back to the server, enqueueing them.

## Setup

### Environment Variables

Create a `.env` file in the project root:

```env
HOST=0.0.0.0
PORT=8000
SERVER_IP=<public IP workers connect to>
API_KEY=<secret key for all API requests>
GOOGLE_PROJECT_ID=<GCP project ID>
GOOGLE_TEMPLATE_NAME=<instance template name>
GOOGLE_DRIVE_FOLDER_ID=<Drive folder for HTML uploads>
SSH_KEYS=<comma-separated SSH public keys>
```

Place GCP service account credentials at `googleCredentials.json` in the project root. Only needed on the server. All secrets needed on the workers get sent to them via metadata. For that reason its heavily recommended to use the endpoints of the server for creation, not googles methods as that may break expected entries in metadata.

The google drive folders id must be a shared one. Otherwise saving will fail. In client/src there is a test_drive.py. Use that to verify the uploading to that folder works.

### Start the Server

Server must be created manually. Run the serverInit.sh found in server/config on it and make sure to allow traffic on the firewall in the google project settings 

When server is up just use its docs page for endpoint interaction `http://<host>:<port>/docs`.
Keep in mind all endpoints (except `/docs` itself) require the `X-API-Key` header to be set. If you use 
the /docs page just put the API_KEY from env into the authorization field for it to happen automatically.

### Start the Workers

Use the /docs page to start workers. By default google only allows 8 vms per zone. So make as many as you want by varying the zones. Available zones are:

us_central1_a
us_central1_b
us_east1_b
europe_west1_b
northamerica_northeast2_b

After a worker is started using /docs it starts working automatically! No need to do anything!

### Progress
Use the /docs endpoint to call /progress to see an overview of the queues. App store has about 1 million apps so expect it to grow to that size.

You can use save checkpoint and load checkpoint endpoints to do exactly that. Load checkpoint overwrites the current state. So not recommended to be used mid run.

### Ending the process
The server does NOT automatically kill the workers. Workers wait for new urls until they get them at some point. If you have enough data or nothing more gets found (You can see that when the available queue is not growing anymore and is 0), use the DELETE endpoints to kill all the workers. 

Its recommended to also save the checkpoint and download it to have a list of all app store urls for future work
