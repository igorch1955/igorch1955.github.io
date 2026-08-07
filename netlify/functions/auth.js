exports.handler = async function (event) {
  const clientId = process.env.OAUTH_CLIENT_ID;
  const host = event.headers['x-forwarded-host'] || event.headers.host;
  const redirectUri = `https://${host}/.netlify/functions/callback`;
  const authorizeUrl =
    `https://github.com/login/oauth/authorize` +
    `?client_id=${clientId}` +
    `&scope=repo,user` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}`;

  return {
    statusCode: 302,
    headers: { Location: authorizeUrl },
    body: '',
  };
};
