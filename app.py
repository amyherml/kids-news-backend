from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import json
from openai import OpenAI
#import schedule
#import time
#import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configure OpenAI API Key
#openai.api_key = os.environ.get('OPENAI_API_KEY')

# Configure database connection
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # Render uses postgres://, need to convert to postgresql://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///news.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define news data model
class NewsArticle(db.Model):
    __tablename__ = 'news_article'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    whatIsHappening = db.Column(db.Text, nullable=False)
    whoIsInvolved = db.Column(db.Text)
    whyImportant = db.Column(db.Text)
    viewpoints = db.Column(db.Text)  # Stored as JSON string
    impacts = db.Column(db.Text)
    imageGroup = db.Column(db.Text)
    storySource = db.Column(db.String(200))
    viewpointSources = db.Column(db.Text)  # Stored as JSON string
    funFact = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    isExample = db.Column(db.Boolean, default=False)  # 确保这一行存在
    
    def to_dict(self):
        """Convert database object to dictionary"""
        result = {
            'title': self.title,
            'category': self.category,
            'whatIsHappening': self.whatIsHappening,
            'whoIsInvolved': self.whoIsInvolved,
            'whyImportant': self.whyImportant,
            'impacts': self.impacts,
            'imageGroup': self.imageGroup,
            'storySource': self.storySource,
            'viewpointSources': json.loads(self.viewpointSources) if self.viewpointSources else [],
            'funFact': self.funFact,
            'isExample': self.isExample,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }
        
        # Handle JSON fields that might be NULL
        if self.viewpoints:
            try:
                result['viewpoints'] = json.loads(self.viewpoints)
            except:
                result['viewpoints'] = []
        else:
            result['viewpoints'] = []
            
        if self.viewpointSources:
            try:
                result['viewpointSources'] = json.loads(self.viewpointSources)
            except:
                result['viewpointSources'] = []
        else:
            result['viewpointSources'] = []
            
        return result

# Create database tables (if not exist)
with app.app_context():
    db.create_all()
    print("✅ Database tables created/verified")

# ---------- Example News (Fallback) ----------
EXAMPLE_NEWS = [
    {
        "headline": "[EXAMPLE] Scientists Discover New Ocean Creature",
        "category": "Science",
        "whatIsHappening": "Scientists have found a glowing fish in the deep ocean! This fish uses its light to attract food and communicate with friends.",
        "whoIsInvolved": "An international team of ocean researchers",
        "whyImportant": "This discovery helps scientists understand deep-sea ecosystems better",
        "viewpoints": [
            {"viewpoint": "Some scientists think this is a major breakthrough"},
            {"viewpoint": "Others believe more research is needed to understand the discovery"}
        ],
        "impacts": "Could lead to new discoveries in marine biology and technology",
        "imageGroup": "Glowing deep sea fish swimming in the ocean",
        "storySource": "BBC",
        "viewpointSources": ["BBC", "CNN"],
        "funFact": "This fish can communicate with light, just like texting!",
        "isExample": True
    },
    {
        "headline": "[EXAMPLE] New Galaxy Discovered by Space Station",
        "category": "Space",
        "whatIsHappening": "Astronauts on the International Space Station found a new galaxy! This galaxy is millions of light-years away.",
        "whoIsInvolved": "NASA astronauts and the International Space Station team",
        "whyImportant": "Helps us understand how the universe began and evolved",
        "viewpoints": [],
        "impacts": "Inspires more young people to study space and astronomy",
        "imageGroup": "A telescope view of a distant spiral galaxy",
        "storySource": "CNN",
        "viewpointSources": [],
        "funFact": "There are more galaxies in the universe than grains of sand on Earth!",
        "isExample": True
    }
]

# ---------- News Generation Function ----------
def generate_news_with_chatgpt():
    """Call ChatGPT to generate daily news"""
    
    prompt = """
You are a professional international news editor writing world news summaries for 10-year-old readers.

Generate the 10 most important global news stories today.

Use reliable international sources such as BBC, NYT, CNN, Der Spiegel, Le Monde, Xinhua, Al Jazeera, FT, etc.

Return JSON:

{
 "news":[
  {
   "headline":"",
   "category":"",
   "whatIsHappening":"",
   "whoIsInvolved":"",
   "whyImportant":"",
   "viewpoints":[{"viewpoint":""}],
   "impacts":"",
   "imageGroup":"",
   "storySource":"",
   "viewpointSources":[],
   "funFact":""
  }
 ]
}

"""
    
    try:
        # Call OpenAI API
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    		
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional international news editor creating news for 10-year-old children."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1800,
            response_format={"type": "json_object"}
        )
        
        # Parse JSON response
        news_data = json.loads(response.choices[0].message.content)
        news_items = news_data.get('news', [])
        
        # Add isExample flag
        for item in news_items:
            item['isExample'] = False
            
        return news_items
        
    except Exception as e:
        print(f"❌ ChatGPT API call failed: {e}")
        return []
        # Return example news with isExample flag
       # example_items = []
       # for item in EXAMPLE_NEWS:
       #     example_items.append(item.copy())
       # return example_items

def save_news_to_db():
    """Generate news and save to database"""
    print(f"📅 [{datetime.now()}] Starting daily news generation...")
    
    # Generate news
    news_items = generate_news_with_chatgpt()
    
    # 调试：打印第一条新闻的所有字段
    if news_items and len(news_items) > 0:
        print("🔥 第一条新闻的字段:")
        for key, value in news_items[0].items():
            print(f"  - {key}: {value}")
    
        # 只有在成功获取到新闻时才保存到数据库
    if news_items and len(news_items) == 10 and not news_items[0].get("isExample", False):
        with app.app_context():
            for item in news_items:
                article = NewsArticle(
                    title=item.get('headline', item.get('title', 'No title')),
                    category=item.get('category', 'General'),
                    whatIsHappening=item.get('whatIsHappening', ''),
                    whoIsInvolved=item.get('whoIsInvolved', ''),
                    whyImportant=item.get('whyImportant', ''),
                    viewpoints=json.dumps(item.get('viewpoints', []), ensure_ascii=False),
                    impacts=item.get('impacts', ''),
                    imageGroup=item.get('imageGroup', ''),
                    storySource=item.get('storySource', ''),
                    viewpointSources=json.dumps(item.get('viewpointSources', []), ensure_ascii=False),
                    funFact=item.get('funFact', ''),
                    isExample=item.get('isExample', False)
                )
               
	

                db.session.add(article)
            
        db.session.commit()
        print(f"✅ Successfully saved {len(news_items)} real news items to database")
    else:
        print("⚠️ No news generated today - database not updated")

        #if len(news_items) != 10:
    	#print("⚠️ Unexpected news count, skipping save")
    	#return

# ---------- Scheduled Task ----------
#def run_schedule():
#    """Run scheduled task in background"""
#    # Run at 1:00 AM every day
#    schedule.every().day.at("01:00").do(save_news_to_db)
    
#    while True:
#        schedule.run_pending()
#        time.sleep(60)

# Start scheduled task thread
#threading.Thread(target=run_schedule, daemon=True).start()
#print("⏰ Scheduled task started, will update news daily at 01:00")

# ---------- API Routes ----------
@app.route('/')
def home():
    """Root path, show API status"""
    return jsonify({
        "status": "Kids News API is running!",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get latest news for website/Android App"""
    try:
        # Get limit parameter (default 10 for website, can be overridden by app)
        limit = request.args.get('limit', default=10, type=int)
        
        # Get today's date at midnight
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Try to get today's news first
        articles = NewsArticle.query.filter(
            NewsArticle.generated_at >= today_start
        ).order_by(NewsArticle.generated_at.desc()).limit(limit).all()
        
        # If no news today, get the most recent news
        if not articles:
            articles = NewsArticle.query.order_by(
                NewsArticle.generated_at.desc()
            ).limit(limit).all()
        
        if articles:
            return jsonify({
                'generated_at': articles[0].generated_at.isoformat(),
                'count': len(articles),
                'news': [a.to_dict() for a in articles]
            })
        else:
            # If no articles in database, return example news
            example_items = []
            for item in EXAMPLE_NEWS:
                example_items.append(item.copy())
            
            return jsonify({
                'generated_at': datetime.now().isoformat(),
                'count': len(example_items),
                'news': example_items,
                'note': 'Showing example news (database empty)'
            })
            
    except Exception as e:
        print(f"❌ Failed to get news: {e}")
        # Return example news on error
        example_items = []
        for item in EXAMPLE_NEWS:
            example_items.append(item.copy())
        
        return jsonify({
            'generated_at': datetime.now().isoformat(),
            'count': len(example_items),
            'news': example_items,
            'error': str(e),
            'note': 'Showing example news due to error'
        })

@app.route('/api/news/today', methods=['GET'])
def get_today_news():
    """Get today's news only"""
    try:
        # Get today's date at midnight
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get today's news
        articles = NewsArticle.query.filter(
            NewsArticle.generated_at >= today_start
        ).order_by(NewsArticle.generated_at.desc()).all()
        
        if articles:
            return jsonify({
                'generated_at': articles[0].generated_at.isoformat(),
                'count': len(articles),
                'news': [a.to_dict() for a in articles]
            })
        else:
            return jsonify({
                'generated_at': datetime.now().isoformat(),
                'count': 0,
                'news': [],
                'note': 'No news generated today yet'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (for cron-job.org)"""
    try:
        db.session.execute('SELECT 1')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    
    return jsonify({
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/refresh', methods=['GET','POST'])
def refresh_news():
    """Manually trigger news refresh (for testing)"""
    try:
        save_news_to_db()
        return jsonify({"status": "success", "message": "News refreshed successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------- Start Application ----------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)