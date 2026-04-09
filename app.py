import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import config
from analyzer.engine import run_analysis

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'document' not in request.files:
            return render_template('index.html', error='No file selected.')
        file = request.files['document']
        if file.filename == '':
            return render_template('index.html', error='No file selected.')
        if not allowed_file(file.filename):
            return render_template('index.html', error='Invalid file type. Allowed: PNG, JPG, JPEG, BMP, TIFF, WEBP.')

        analysis_id = uuid.uuid4().hex[:8]
        ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        filename = f"{analysis_id}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        return redirect(url_for('report', analysis_id=analysis_id, filename=filename))

    return render_template('index.html')


@app.route('/report/<analysis_id>/<filename>')
def report(analysis_id, filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return redirect(url_for('index'))

    result = run_analysis(filepath, analysis_id)
    return render_template('report.html', result=result, filename=filename)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
    port = int(os.environ.get('PORT', 8005))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
