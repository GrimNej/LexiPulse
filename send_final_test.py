#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/home/ubuntu/LexiPulse')

from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from config import settings
from models import User
from services.email_service import render_newsletter_email, send_email
from services.content_agent import generate_newsletter_with_qa
from services.web_search import search_web, format_search_context, build_search_query
from services.token_service import generate_unsubscribe_token

async def main():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == 'ginejneupane123@gmail.com'))
        user = result.scalar_one_or_none()
        if not user:
            print("User not found!")
            return
        
        prompt = "Latest AI industry news with the most relevant and engaging updates. Include key statistics, funding rounds, and new model releases."
        date_str = date.today().strftime("%B %d, %Y")
        
        query = build_search_query(prompt, date_str)
        print(f"[Search] Query: {query}")
        results = await search_web(query, max_results=5)
        print(f"[Search] Found {len(results)} results")
        for r in results:
            print(f"  - {r['title'][:60]}...")
        
        ctx = format_search_context(results)
        
        print(f"\n[Generate] Running with QA...")
        content = await generate_newsletter_with_qa(prompt, date_str, search_context=ctx, max_attempts=2)
        
        print(f"\n=== RESULT ===")
        print(f"Title: {content['title']}")
        print(f"Mood: {content['mood']}")
        print(f"Sources: {len(content.get('sources', []))}")
        for src in content.get('sources', []):
            print(f"  - {src['title']}: {src['url']}")
        
        for i, sec in enumerate(content['sections']):
            print(f"\n[{i+1}] {sec['component']} | heading: {sec['heading'][:40] if sec['heading'] else '(empty)'}...")
            print(f"    content: {sec['content'][:90]}...")
            if sec.get('source_url'):
                print(f"    source:  {sec['source_url'][:60]}...")
            else:
                print(f"    source:  (none)")
        
        print(f"\nClosing: {content['closing']}")
        
        html = render_newsletter_email(
            user_name=user.name, user_id=user.id,
            title=content['title'], subtitle=content.get('subtitle', date_str),
            mood=content.get('mood', 'minimal'), sections=content['sections'],
            closing=content.get('closing', 'Until tomorrow.'),
            token="final-test", send_date=date.today().strftime("%B %d"),
            unsubscribe_token=user.unsubscribe_token or generate_unsubscribe_token(),
            sources=content.get('sources', []),
        )
        
        if '\\n' in html:
            print("\n*** WARNING: literal \\n found in HTML ***")
        else:
            print("\n[OK] No literal \\n in HTML")
        
        if 'color:font-family' in html:
            print("*** WARNING: broken CSS detected ***")
        else:
            print("[OK] No broken CSS injection")
        
        with open("/tmp/final_newsletter.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        mid = await send_email(user.email, content['title'], html)
        print(f"\n[SENT] Resend ID: {mid}")

if __name__ == "__main__":
    asyncio.run(main())
