"""Configure Telegram callbacks after deployment. --check is read-only."""
import argparse
import getpass
import os
import re
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv


def run():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    token = (os.getenv('TELEGRAM_BOT_TOKEN') or getpass.getpass('TELEGRAM_BOT_TOKEN (hidden): ')).strip()
    if not token:
        raise SystemExit('Bot token is required.')

    def api(method, payload=None):
        try:
            response = requests.post('https://api.telegram.org/bot'+token+'/'+method,
                                     json=payload or {}, timeout=(5,20))
            data = response.json()
        except (requests.RequestException, ValueError):
            raise SystemExit('Telegram connection failed. Check your network and bot token.') from None
        if not response.ok or not data.get('ok'):
            raise SystemExit('Telegram API rejected the request (HTTP '+str(response.status_code)+'). Check bot token/settings.')
        return data.get('result')

    def status(info):
        print('Webhook URL:', info.get('url') or '(not configured)')
        print('Pending updates:', info.get('pending_update_count',0))
        if info.get('last_error_message'):
            print('Last delivery error:', str(info['last_error_message']).replace(token,'[hidden]'))
        print('Allowed updates:', ', '.join(info.get('allowed_updates',[])) or '(default)')

    status(api('getWebhookInfo'))
    if args.check:
        return
    default = os.getenv('PUBLIC_BASE_URL','https://miners-villa-bot.onrender.com').rstrip('/')
    base = (input('Render URL ['+default+']: ').strip() or default).rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme!='https' or not parsed.netloc or parsed.query or parsed.fragment:
        raise SystemExit('Enter the HTTPS service URL without a query or fragment.')
    secret = os.getenv('TELEGRAM_WEBHOOK_SECRET') or getpass.getpass('TELEGRAM_WEBHOOK_SECRET (EXACT same value as Render, hidden): ')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',secret):
        raise SystemExit('Secret must contain only A-Z, a-z, 0-9, _ or - (1 to 256 characters).')
    target = base+'/telegram/webhook'
    api('setWebhook', {'url':target, 'secret_token':secret,
                      'allowed_updates':['callback_query'], 'drop_pending_updates':False})
    info = api('getWebhookInfo')
    status(info)
    if info.get('url')!=target:
        raise SystemExit('Webhook URL verification failed.')
    print('Webhook registered. Now click a NEW Telegram request button to test delivery and admin permission.')
    print('Registration alone does not verify the Render secret. HTTP 403 means the secrets do not match.')


if __name__=='__main__':
    run()
