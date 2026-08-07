exports.handler = async function (event) {
  const code = event.queryStringParameters && event.queryStringParameters.code;
  const clientId = process.env.OAUTH_CLIENT_ID;
  const clientSecret = process.env.OAUTH_CLIENT_SECRET;

  if (!code) {
    return { statusCode: 400, body: 'Missing code parameter.' };
  }

  const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      code: code,
    }),
  });

  const tokenData = await tokenRes.json();

  if (tokenData.error || !tokenData.access_token) {
    return {
      statusCode: 400,
      body: 'OAuth error: ' + (tokenData.error_description || JSON.stringify(tokenData)),
    };
  }

  const token = tokenData.access_token;
  const content = JSON.stringify({ token, provider: 'github' });

  const script = `
    <!DOCTYPE html>
    <html><body>
    <script>
      (function() {
        function receiveMessage(e) {
          window.opener.postMessage(
            'authorization:github:success:${content.replace(/'/g, "\\'")}',
            e.origin
          );
          window.removeEventListener('message', receiveMessage, false);
        }
        window.addEventListener('message', receiveMessage, false);
        window.opener.postMessage('authorizing:github', '*');
      })();
    </script>
    </body></html>
  `;

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'text/html' },
    body: script,
  };
};
