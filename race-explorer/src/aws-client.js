import { S3Client, ListObjectsV2Command, GetObjectCommand } from '@aws-sdk/client-s3';
import { CognitoIdentityClient } from "@aws-sdk/client-cognito-identity";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-providers";
import { createBaseLoader } from './util.js';
import * as config from './aws-config.js';

function createLoader(client, bucket, prefix) {
  const loader = createBaseLoader();
  loader.client = client;
  loader.bucket = bucket;
  loader.prefix = prefix;
  loader._load = async function(processor) {
    const opts = {abortSignal: this.aborter.signal};
    try {
      const s3objList = await this.client.send(new ListObjectsV2Command({
        Bucket: this.bucket,
        Prefix: this.prefix
      }), opts);
      const data = {};
      for (const s3obj of s3objList.Contents) {
        if (!(s3obj.key in this.s3Cache) || this.s3Cache[s3obj.key].etag !== s3obj.ETag) {
          const s3objData = await client.send(new GetObjectCommand({
            Bucket: this.bucket,
            Key: s3obj.Key
          }), opts);
          const body = await new Response(s3objData.Body).text();
          this.s3Cache[s3obj.key] = {etag: s3obj.ETag, contents: body};
        }
        const contents = this.s3Cache[s3obj.key].contents;
        if (processor !== null) {
          processor(contents, data);
        } else {
          Object.assign(data, contents);
        }
      }
      return data;
    } catch (err) {
      if (err?.name === 'NotAuthorizedException') {
        window.location = config.LOGIN_URL+'&response_type=token&redirect_uri='+window.location;
        throw err;
      } else {
        throw err;
      }
    }
  };
  return loader;
}

function getAuthToken() {
  let authToken = null;
  if (window.location.hash.length > 0) {
    const params = new URLSearchParams(window.location.hash.substring(1));
    authToken = params.get('id_token');
  }
  return authToken;
}

let client = null;

function createClient(authToken) {
  if (client === null) {
    const loginTokens = {};
    if (authToken) {
      loginTokens[config.LOGIN] = authToken;
    }
  
    client = new S3Client({
      region: config.REGION,
      credentials: fromCognitoIdentityPool({
        client: new CognitoIdentityClient({region: config.REGION}),
        identityPoolId: config.IDENTITY_POOL_ID,
        logins: loginTokens,
        clientConfig: {region: config.REGION}
      })
    });
  }
  return client;
}

export function createResultDataLoader() {
  const authToken = getAuthToken();
  const s3client = createClient(authToken);
  return createLoader(s3client, config.BUCKET, 'log-');
}
