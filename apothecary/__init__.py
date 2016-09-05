import boto3
from flask import Flask, render_template, g
from .model import NavGroup, Nav, SectionGroup, Section, Couple
from .auth import ApothecaryRealmDigestDB

app = Flask(__name__)
app.config.from_object('websiteconfig')
authDB = ApothecaryRealmDigestDB('ApothecaryAuth')

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
    g.dynamodb = boto3.resource('dynamodb')
    header_nav = NavGroup.get(g.dynamodb, 'header_nav')
    footer_nav = NavGroup.get(g.dynamodb, 'footer_nav')
    couple = Couple.get(g.dynamodb, '0')

    g.nav_bar = header_nav.navs
    g.toes = footer_nav.navs
    g.her = couple.her
    g.him = couple.him
    g.title = g.her.split(' ')[0] + ' & ' + g.him.split(' ')[0]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/story/')
def story():
    story = SectionGroup.get(g.dynamodb, 'story')
    sections = story.sections
    return render_template('sections.html', **locals())


@app.route('/event/')
def event():
    event = SectionGroup.get(g.dynamodb, 'event')
    sections = event.sections
    return render_template('sections.html', **locals())


@app.route('/travel/')
def travel():
    travel = SectionGroup.get(g.dynamodb, 'travel')
    sections = travel.sections
    return render_template('sections.html', **locals())


@app.route('/area/')
def area():
    area = SectionGroup.get(g.dynamodb, 'area')
    sections = area.sections
    return render_template('sections.html', **locals())


@app.route('/needs_auth/')
@authDB.requires_auth
def test_auth():
    return 'Successful auth!'
