from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3, os, re, json
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'patient_food.db')
UPLOADS = os.path.join(BASE, 'uploads')
os.makedirs(UPLOADS, exist_ok=True)
app = Flask(__name__)
app.secret_key = 'patient-food-offline-demo'

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
MEALS = ['breakfast','lunch','dinner']

FOOD = {
 'diabetes': {
  'label':'Elevated Blood Sugar / Diabetes Risk',
  'eat':['Oats','Ragi','Millets','Green leafy vegetables','Boiled egg','Guava','Sprouts'],
  'avoid':['Sweets','Sugary drinks','Refined sugar','Sweetened bakery foods','Large portions of white rice'],
  'breakfast':['Vegetable oats + boiled egg','2 idly + sambar + guava','Ragi dosa + egg','Millet upma + vegetables','Oats + apple + boiled egg','Vegetable dosa + curd','Ragi idly + sambar'],
  'lunch':['Millet rice + vegetables + dal + curd','Controlled rice + greens + dal','Ragi/millet + vegetables + egg','Brown rice + beans + dal','Millet + spinach + dal + curd','Vegetable millet upma + dal','Controlled rice + vegetables + rasam'],
  'dinner':['2 vegetable dosa + egg','2 idly + vegetable sambar','Ragi dosa + vegetable side','Vegetable soup + 2 dosa','2 millet dosa + dal','Vegetable oats + egg','2 dosa + greens + curd']},
 'hypertension': {
  'label':'Elevated Blood Pressure / Hypertension Risk',
  'eat':['Oats','Banana','Guava','Vegetables','Unsalted nuts','Low-fat curd','Dal','Whole grains'],
  'avoid':['Pickles','Papad','Very salty snacks','Instant noodles','Processed meat','Excess packaged foods'],
  'breakfast':['Oats + banana + unsalted nuts','Idly + low-salt sambar + fruit','Vegetable dosa + guava','Oats + apple','Ragi idly + low-salt sambar','Vegetable upma + fruit','Dosa + banana + unsalted nuts'],
  'lunch':['Low-salt millet + vegetables + dal','Rice + greens + low-salt dal','Millet + beans + vegetables + curd','Brown rice + vegetable kootu','Millet + spinach + dal','Rice + vegetables + dal','Balanced low-salt South Indian meal'],
  'dinner':['Vegetable dosa','2 idly + vegetable sambar','Vegetable soup + dosa','Ragi dosa + vegetables','Light millet dosa + dal','Idly + vegetables','Dosa + vegetable side']},
 'cholesterol': {
  'label':'Elevated Cholesterol Risk',
  'eat':['Oats','Millets','Vegetables','Fruits','Dal','Sprouts','Flax seeds','Low-fat curd'],
  'avoid':['Deep-fried foods','Trans-fat bakery foods','Processed meat','Excess ghee','Excess butter','Fried snacks'],
  'breakfast':['Oats + apple + flax seeds','Idly + sambar + guava','Ragi dosa + fruit','Vegetable oats','Oats + banana + nuts','Millet upma + vegetables','Dosa + fruit + low-fat curd'],
  'lunch':['Millet + vegetables + dal','Brown rice + greens + dal','Millet + beans + vegetables','Rice + vegetable kootu + dal','Millet + spinach + curd','Vegetable millet meal + sprouts','Balanced low-fat South Indian meal'],
  'dinner':['Vegetable dosa + dal','Vegetable soup + 2 idly','Ragi dosa + vegetables','Millet dosa + dal','2 dosa + vegetable side','Oats + vegetables','Idly + vegetable sambar']},
 'anaemia': {
  'label':'Low Haemoglobin / Anaemia Risk',
  'eat':['Spinach','Drumstick leaves','Lentils','Beans','Boiled egg','Guava','Amla','Sesame seeds'],
  'avoid':['Tea immediately with meals','Coffee immediately with meals','Highly processed snacks','Skipping iron-rich meals'],
  'breakfast':['Dosa + boiled egg + guava','Idly + sambar + amla','Oats + egg + fruit','Ragi dosa + guava','Vegetable dosa + egg','Millet upma + fruit','Dosa + egg + amla'],
  'lunch':['Rice + spinach + dal + lemon','Millet + drumstick leaves + beans','Rice + greens + lentils + lemon','Millet + spinach + dal','Rice + drumstick leaves + egg','Millet + beans + greens','Rice + greens + dal + lemon'],
  'dinner':['Dosa + greens + egg','Idly + spinach sambar','Ragi dosa + egg','Vegetable dosa + greens','Millet dosa + dal','Idly + greens + egg','Dosa + spinach + dal']},
 'normal': {
  'label':'General Balanced Diet',
  'eat':['Vegetables','Fruits','Whole grains','Dal','Egg','Curd','Nuts','Millets'],
  'avoid':['Excess sugary foods','Deep-fried foods','Excess processed foods','Sugary drinks'],
  'breakfast':['Oats + egg + fruit','Idly + sambar + fruit','Dosa + egg + fruit','Vegetable upma + curd','Ragi dosa + fruit','Oats + nuts + banana','Idly + vegetable sambar'],
  'lunch':['Rice + vegetables + dal + curd','Millet + vegetables + dal','Rice + greens + egg + vegetables','Millet + beans + curd','Rice + vegetable kootu + dal','Millet + vegetables + sprouts','Balanced South Indian meal'],
  'dinner':['Dosa + vegetables','Idly + sambar','Vegetable dosa + egg','Ragi dosa + vegetables','Millet dosa + dal','Light vegetable upma','Dosa + vegetables + curd']}
}

# --- database ---
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c=db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,age TEXT,gender TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id INTEGER NOT NULL,filename TEXT NOT NULL,extracted_text TEXT,blood_sugar REAL,cholesterol REAL,haemoglobin REAL,systolic INTEGER,diastolic INTEGER,analysis TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS schedules(patient_id INTEGER NOT NULL,day TEXT NOT NULL,breakfast TEXT NOT NULL,lunch TEXT NOT NULL,dinner TEXT NOT NULL,PRIMARY KEY(patient_id,day));
    CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),breakfast_time TEXT NOT NULL,lunch_time TEXT NOT NULL,dinner_time TEXT NOT NULL);
    ''')
    if not c.execute('SELECT id FROM settings WHERE id=1').fetchone():
        c.execute("INSERT INTO settings VALUES(1,'08:00','13:00','20:00')")
    c.commit(); c.close()

# --- report extraction ---
def read_pdf(path):
    try:
        from pypdf import PdfReader
        return '\n'.join((p.extract_text() or '') for p in PdfReader(path).pages)
    except Exception:
        return ''

def num(text, patterns):
    for p in patterns:
        m=re.search(p,text,re.I|re.M)
        if m:
            try:return float(m.group(1))
            except ValueError: pass
    return None

def extract_values(text):
    sugar=num(text,[r'blood\s*sugar\s*[:=\-]?\s*(\d+(?:\.\d+)?)',r'blood\s*glucose\s*[:=\-]?\s*(\d+(?:\.\d+)?)',r'glucose\s*[:=\-]?\s*(\d+(?:\.\d+)?)'])
    chol=num(text,[r'total\s*cholesterol\s*[:=\-]?\s*(\d+(?:\.\d+)?)',r'cholesterol\s*[:=\-]?\s*(\d+(?:\.\d+)?)'])
    hb=num(text,[r'haemoglobin\s*[:=\-]?\s*(\d+(?:\.\d+)?)',r'hemoglobin\s*[:=\-]?\s*(\d+(?:\.\d+)?)',r'\bhb\s*[:=\-]?\s*(\d+(?:\.\d+)?)'])
    bp=re.search(r'(?:blood\s*pressure|bp)\s*[:=\-]?\s*(\d{2,3})\s*/\s*(\d{2,3})',text,re.I)
    if not bp: bp=re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s*mmhg',text,re.I)
    return sugar,chol,hb,(int(bp.group(1)) if bp else None),(int(bp.group(2)) if bp else None)

def analyze(sugar,chol,hb,sys,dia):
    keys=[]; flags=[]
    if sugar is not None and sugar>=126: keys.append('diabetes'); flags.append(f'Blood sugar {sugar:g} mg/dL is elevated.')
    if sys is not None and dia is not None and (sys>=140 or dia>=90): keys.append('hypertension'); flags.append(f'Blood pressure {sys}/{dia} mmHg is elevated.')
    if chol is not None and chol>=200: keys.append('cholesterol'); flags.append(f'Cholesterol {chol:g} mg/dL is elevated.')
    if hb is not None and hb<12: keys.append('anaemia'); flags.append(f'Haemoglobin {hb:g} g/dL is low.')
    if not keys: keys=['normal']
    eat=[]; avoid=[]
    for k in keys:
        for x in FOOD[k]['eat']:
            if x not in eat:eat.append(x)
        for x in FOOD[k]['avoid']:
            if x not in avoid:avoid.append(x)
    return {'keys':keys,'condition':' + '.join(FOOD[k]['label'] for k in keys),'flags':flags,'eat':eat,'avoid':avoid}

def generate_schedule(keys):
    # Rotate across every detected condition, so different days are not identical.
    if not keys: keys=['normal']
    sources=[FOOD[k] for k in keys]
    out=[]
    for i,day in enumerate(DAYS):
        b=sources[i%len(sources)]['breakfast'][i]
        l=sources[(i+1)%len(sources)]['lunch'][i]
        d=sources[(i+2)%len(sources)]['dinner'][i]
        out.append((day,b,l,d))
    return out

def ensure_schedule(pid,keys):
    c=db()
    for row in generate_schedule(keys):
        c.execute('INSERT OR REPLACE INTO schedules(patient_id,day,breakfast,lunch,dinner) VALUES(?,?,?,?,?)',(pid,*row))
    c.commit();c.close()

@app.route('/')
def home():
    c=db(); reports=c.execute('''SELECT r.*,p.name,p.age,p.gender,json_extract(r.analysis,'$.condition') AS condition FROM reports r JOIN patients p ON p.id=r.patient_id ORDER BY r.id DESC''').fetchall(); c.close()
    return render_template('index.html',reports=reports)

@app.route('/upload',methods=['GET','POST'])
def upload():
    if request.method=='POST':
        f=request.files.get('report'); name=request.form.get('name','').strip()
        if not name or not f or not f.filename.lower().endswith('.pdf'):
            flash('Enter patient name and select a PDF report.'); return redirect(url_for('upload'))
        safe=re.sub(r'[^A-Za-z0-9_.-]','_',f.filename); filename=datetime.now().strftime('%Y%m%d_%H%M%S_')+safe
        path=os.path.join(UPLOADS,filename); f.save(path)
        text=read_pdf(path); sugar,chol,hb,sys,dia=extract_values(text)
        a=analyze(sugar,chol,hb,sys,dia)
        c=db(); pid=c.execute('INSERT INTO patients(name,age,gender,created_at) VALUES(?,?,?,?)',(name,request.form.get('age',''),request.form.get('gender',''),datetime.now().isoformat(timespec='seconds'))).lastrowid
        rid=c.execute('''INSERT INTO reports(patient_id,filename,extracted_text,blood_sugar,cholesterol,haemoglobin,systolic,diastolic,analysis,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',(pid,filename,text,sugar,chol,hb,sys,dia,json.dumps(a),datetime.now().isoformat(timespec='seconds'))).lastrowid
        for row in generate_schedule(a['keys']): c.execute('INSERT OR REPLACE INTO schedules VALUES(?,?,?,?,?)',(pid,*row))
        c.commit();c.close();return redirect(url_for('result',rid=rid))
    return render_template('upload.html')

@app.route('/result/<int:rid>')
def result(rid):
    c=db(); r=c.execute('SELECT r.*,p.name,p.age,p.gender FROM reports r JOIN patients p ON p.id=r.patient_id WHERE r.id=?',(rid,)).fetchone(); c.close()
    if not r:return 'Report not found',404
    return render_template('result.html',r=r,a=json.loads(r['analysis']))

@app.route('/schedule/<int:rid>',methods=['GET','POST'])
def schedule(rid):
    c=db(); r=c.execute('SELECT r.*,p.name FROM reports r JOIN patients p ON p.id=r.patient_id WHERE r.id=?',(rid,)).fetchone()
    if not r:return 'Report not found',404
    if request.method=='POST':
        for day in DAYS:
            c.execute('UPDATE schedules SET breakfast=?,lunch=?,dinner=? WHERE patient_id=? AND day=?',(request.form[f'b_{day}'],request.form[f'l_{day}'],request.form[f'd_{day}'],r['patient_id'],day))
        c.commit(); flash('Weekly food plan saved for this patient.')
    rows=c.execute("SELECT * FROM schedules WHERE patient_id=? ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 END",(r['patient_id'],)).fetchall()
    s=c.execute('SELECT * FROM settings WHERE id=1').fetchone();c.close();return render_template('schedule.html',r=r,rows=rows,s=s)

@app.route('/settings',methods=['GET','POST'])
def settings():
    c=db()
    if request.method=='POST':
        c.execute('UPDATE settings SET breakfast_time=?,lunch_time=?,dinner_time=? WHERE id=1',(request.form['breakfast_time'],request.form['lunch_time'],request.form['dinner_time']));c.commit();flash('Three daily notification times saved.')
    s=c.execute('SELECT * FROM settings WHERE id=1').fetchone();c.close();return render_template('settings.html',s=s)

@app.route('/notifications/<int:rid>')
def notifications(rid):
    c=db();r=c.execute('SELECT r.*,p.name FROM reports r JOIN patients p ON p.id=r.patient_id WHERE r.id=?',(rid,)).fetchone();s=c.execute('SELECT * FROM settings WHERE id=1').fetchone();c.close();return render_template('notifications.html',r=r,s=s)

@app.route('/api/notification/<meal>/<int:rid>')
def notification(meal,rid):
    c=db();r=c.execute('SELECT patient_id FROM reports WHERE id=?',(rid,)).fetchone();day=datetime.now().strftime('%A');q=c.execute('SELECT * FROM schedules WHERE patient_id=? AND day=?',(r['patient_id'],day)).fetchone();p=c.execute('SELECT name FROM patients WHERE id=?',(r['patient_id'],)).fetchone();c.close()
    return jsonify(title=f'{meal.title()} Food Reminder',body=f"{p['name']}: {q[meal] if q else 'See weekly plan'}")

if __name__=='__main__':
    init_db(); app.run(host='127.0.0.1',port=5000,debug=False)
