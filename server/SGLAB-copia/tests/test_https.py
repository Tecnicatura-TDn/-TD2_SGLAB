"""Verifica el transporte real, sin desactivar la validación del certificado."""
import os
import ssl
import unittest
import urllib.error
import urllib.request
from test_web_integration import BASE, Browser, tls_context


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB') == '1', 'SGLAB_TEST_WEB=1 para HTTPS real')
class HttpsIntegration(unittest.TestCase):
    def test_certificate_and_cookies(self):
        self.assertTrue(BASE.startswith('https://'))
        browser = Browser()
        status, html, headers = browser.request('login')
        self.assertEqual(status, 200)
        self.assertIn('name="password"', html)
        self.assertTrue(next(cookie for cookie in browser.cookies if cookie.name == 'sglab_session').secure)
        # La CA aún no está instalada en el almacén global del servidor.
        # Una CA distinta debe fallar, nunca aceptar cualquier certificado.
        wrong_ca = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with self.assertRaises(urllib.error.URLError) as failure:
            urllib.request.urlopen(BASE, context=wrong_ca, timeout=10)
        self.assertIsInstance(failure.exception.reason, ssl.SSLCertVerificationError)

    def test_http_redirect_and_no_plaintext_form(self):
        opener = urllib.request.build_opener(NoRedirect())
        http = os.environ.get('SGLAB_HTTP_URL', 'http://127.0.0.1:8080')
        request = urllib.request.Request(http + '/?page=login', headers={'Host': 'untrusted.example'})
        with self.assertRaises(urllib.error.HTTPError) as redirect:
            opener.open(request, timeout=10)
        self.assertEqual(redirect.exception.code, 301)
        target = redirect.exception.headers['Location']
        self.assertTrue(target.startswith('https://'))
        self.assertNotIn('untrusted.example', target)
        self.assertTrue(target.endswith('/?page=login'))
        # La redirección preserva la ruta y el destino presenta una firma/IP válida.
        with urllib.request.urlopen(target, context=tls_context(), timeout=10) as response:
            self.assertEqual(response.status, 200)
        with self.assertRaises(urllib.error.HTTPError) as denied:
            opener.open(http + '/', data=b'action=login', timeout=10)
        self.assertEqual(denied.exception.code, 403)
        self.assertNotIn('Set-Cookie', denied.exception.headers)
