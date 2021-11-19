import { S3Client, ListObjectsV2Command, GetObjectCommand } from '@aws-sdk/client-s3';
import { CognitoIdentityClient } from "@aws-sdk/client-cognito-identity";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-providers";
import * as config from './aws-config.js';

export default function createEventDataLoader() {
  const authToken = getAuthToken();
  let loginTokens = {};
  if (authToken) {
    loginTokens[config.LOGIN] = authToken;
  }

  const s3client = new S3Client({
    region: config.REGION,
    credentials: fromCognitoIdentityPool({
      client: new CognitoIdentityClient({region: config.REGION}),
      identityPoolId: config.IDENTITY_POOL_ID,
      logins: loginTokens,
      clientConfig: {region: config.REGION}
    })
  });

  return (processEvents, raceEvents) => loadEventData(s3client, processEvents, raceEvents);
}

function getAuthToken() {
  let authToken = null;
  if (window.location.hash.length > 0) {
    const params = new URLSearchParams(window.location.hash.substring(1));
    authToken = params.get('id_token');
  }
  return authToken;
}

let s3Cache = {};

async function loadEventData(client, processEvents, raceEvents) {
  if (!client) {
    return;
  }

  try {
    const s3objList = await client.send(new ListObjectsV2Command({
      Bucket: config.BUCKET,
      Prefix: 'log-'
    }));
    for (const s3obj of s3objList.Contents) {
      if (!(s3obj.key in s3Cache) || s3Cache[s3obj.key].etag !== s3obj.ETag) {
        const s3objData = await client.send(new GetObjectCommand({
          Bucket: config.BUCKET,
          Key: s3obj.Key
        }));
        const body = await new Response(s3objData.Body).text();
        s3Cache[s3obj.key] = {etag: s3obj.ETag, contents: body};
      }
      const contents = s3Cache[s3obj.key].contents;
      processEvents(contents, raceEvents);
    }
  } catch (err) {
    if (err.name === 'NotAuthorizedException') {
      window.location = config.LOGIN_URL+'&response_type=token&redirect_uri='+window.location;
    } else {
      console.log(err);
    }
  }
}
