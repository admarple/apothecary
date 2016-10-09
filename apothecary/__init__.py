import boto3
from flask import Flask, render_template, g, request, redirect, url_for
from flask.ext.misaka import Misaka
from .model import NavGroup, Nav, SectionGroup, Section, Couple, RSVP, Accommodation

app = Flask(__name__)
app.config.from_object('websiteconfig')
Misaka(app)

if not app.debug:
    import logging
    from logging import Formatter
    from logging.handlers import TimedRotatingFileHandler

    file_handler = TimedRotatingFileHandler('apothecary.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(Formatter(
        ' | '.join(['%(asctime)s',
                    '%(levelname)s',
                    '%(message)s',
                    '%(pathname)s',
                    '%(funcName)s',
                    '%(lineno)d'])
    ))
    app.logger.addHandler(file_handler)


@app.before_request
def bind_common():
    g.dynamodb = boto3.resource('dynamodb', region_name=app.config['AWS_REGION'])
    header_nav = NavGroup.get(g.dynamodb, 'header_nav')
    footer_nav = NavGroup.get(g.dynamodb, 'footer_nav')
    couple = Couple.get(g.dynamodb, '0')

    g.nav_bar = header_nav.navs
    g.toes = footer_nav.navs
    g.her = couple.her
    g.him = couple.him
    g.accommodations = couple.accommodations
    g.title = g.her.split(' ')[0] + ' & ' + g.him.split(' ')[0]


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping')
def ping():
    return 'healthy'

@app.route('/story/')
def story():
    active_page = 'story'
    story = SectionGroup.get(g.dynamodb, active_page)
    sections = story.sections
    return render_template('sections.html', **locals())


@app.route('/event/')
def event():
    active_page = 'event'
    event = SectionGroup.get(g.dynamodb, active_page)
    sections = event.sections
    return render_template('sections.html', **locals())


@app.route('/travel/')
def travel():
    active_page = 'travel'
    travel = SectionGroup.get(g.dynamodb, active_page)
    sections = travel.sections
    if g.accommodations:
        accommodations = sorted([accommodation for accommodation in Accommodation.scan(g.dynamodb)], key=lambda x: x.miles_to_reception)
    return render_template('travel.html', **locals())


@app.route('/area/')
def area():
    active_page = 'area'
    area = SectionGroup.get(g.dynamodb, active_page)
    sections = area.sections
    return render_template('sections.html', **locals())


@app.route('/party/')
def party():
    active_page = 'party'
    party = SectionGroup.get(g.dynamodb, active_page)
    sections = party.sections
    return render_template('party.html', **locals())


@app.route('/save-the-date/', methods=['GET', 'POST'])
def save_the_date():
    if request.method == 'GET':
        active_page = 'save-the-date'
        save = SectionGroup.get(g.dynamodb, active_page)
        sections = save.sections
        accommodations = sorted([accommodation for accommodation in Accommodation.scan(g.dynamodb)], key=lambda x: x.miles_to_reception)
        return render_template('save-the-date.html', **locals())
    elif request.method == 'POST':
        rsvp = RSVP(request.form['name'],
                    request.form['email'],
                    request.form['address'],
                    request.form['guests'],
                    request.form.getlist('hotel_preference'),
                    request.form['notes']
        )
        if 'decline' in request.form:
            rsvp.declined = True
        rsvp.put(g.dynamodb)
        return render_template('save-the-date-submit.html', **locals())