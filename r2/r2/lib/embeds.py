from datetime import datetime
import math
from pylons import c, g, request
from pylons.controllers.util import abort
import pytz

from r2.controllers.reddit_base import UnloggedUser
from r2.models import Account, NotFound
from r2.models.subreddit import Subreddit


def embeddable_sr(thing):
    if isinstance(thing, Subreddit):
        sr = thing
    else:
        try:
            sr = Subreddit._byID(thing.sr_id, data=True) if thing.sr_id else None
        except NotFound:
            sr = None

    return sr if (sr is not None and sr.type not in Subreddit.private_types) else False


def edited_after(thing, iso_timestamp, showedits):
    if not thing:
        return False

    if not isinstance(getattr(thing, "editted", False), datetime):
        return False

    try:
        created = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return not showedits

    created = created.replace(tzinfo=pytz.utc)

    return created < thing.editted


def prepare_embed_request(sr):
    """Given a request, determine if we are embedding. If so, ensure the
       subreddit is embeddable and prepare the request for embedding.
    """
    is_embed = request.GET.get('embed')

    if not is_embed:
        return None

    if request.host != g.media_domain:
        # don't serve up untrusted content except on our
        # specifically untrusted domain
        abort(404)

    if not embeddable_sr(sr):
        abort(404)

    c.allow_framing = True

    return is_embed


def set_up_embed(sr, thing, showedits):
    try:
        author = Account._byID(thing.author_id) if thing.author_id else None
    except NotFound:
        author = None

    iso_timestamp = request.GET.get("created", "")

    c.embed_config = {
        "eventtracker_url": g.eventtracker_url or "",
        "anon_eventtracker_url": g.anon_eventtracker_url or "",
        "event_clicktracker_url": g.event_clicktracker_url or "",
        "created": iso_timestamp,
        "showedits": showedits,
        "thing": {
            "id": thing._id,
            "sr_id": sr._id,
            "sr_name": sr.name,
            "edited": edited_after(thing, iso_timestamp, showedits),
            "deleted": thing.deleted or author._deleted,
        },
        "comment_max_height": 200,
    }

    c.render_style = "iframe"
    c.user = UnloggedUser([c.lang])
    c.user_is_loggedin = False
    c.forced_loggedout = True


def is_embed():
    return c.render_style == "iframe"
