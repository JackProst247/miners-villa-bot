"""Run manually after setting environment and deploying HTTPS service."""
import os
import requests
from dotenv import load_dotenv
load_dotenv()
if __name__=='__main__':
    base=os.environ['PUBLIC_BASE_URL'].rstrip('/')
    if not base.startswith('https://'): raise SystemExit('PUBLIC_BASE_URL must be HTTPS')
    result=requests.post(
        'https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/setWebhook',
        json={'url':base+'/telegram/webhook',
              'secret_token':os.environ['TELEGRAM_WEBHOOK_SECRET'],
              'allowed_updates':['callback_query'],'drop_pending_updates':False},timeout=20)
    print('Webhook configured.' if result.ok and result.json().get('ok') else 'Failed; check Telegram settings.')
