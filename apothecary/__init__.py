from flask import Flask, render_template, g
from . import model

app = Flask(__name__)
app.config.from_object('websiteconfig')

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
    g.him = 'Alex Marple'
    g.her = 'Tatiana McLauchlan'
    g.nav_bar = [{"href": '/', "id": 'index', "caption": 'a M t'},
               {"href": '/story/', "id": 'story', "caption": 'Our Story'}]
    g.toes = [{"href": 'https://github.com/admarple/apothecary', "id": 'github', "caption": 'Source on GitHub'}]
    g.title = g.her.split(' ')[0] + ' & ' + g.him.split(' ')[0]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/story/')
def story():
    section_group_id = 'story'
    sections = [{"title": 'Tatiana', "text": 'Tatiana is the best :D'},
                {"title": 'Alex', "text": 'Alex is a shit ball :P'},
                {'title': 'Our Story', "text": 'Tat and Alex met in 2010 in Philadelphia. Their relationship' +
                                               ' has taken them (by different paths) to New York.'}]
    return render_template('sections.html', **locals())

if __name__ == '__main__':
    model.setup()
    app.run()
