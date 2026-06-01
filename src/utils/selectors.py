"""Centralized DOM selectors for X (Twitter).

**This is the single source of truth for every CSS / data-testid selector
used across the utility modules.**  When X ships a DOM change, update
*only this file* and all tools stay in sync.

Selectors are grouped by page / feature area.  Names use UPPER_SNAKE_CASE
so they read like constants at the call-site.
"""

# ---------------------------------------------------------------------------
# Tweet / article
# ---------------------------------------------------------------------------

TWEET_ARTICLE = 'article[data-testid="tweet"]'
TWEET_TEXT = '[data-testid="tweetText"]'
TWEET_USER_NAME = '[data-testid="User-Name"]'
TWEET_TIMESTAMP = "time"  # <time datetime="..."> inside the tweet
TWEET_PERMALINK = f"{TWEET_USER_NAME} a[href*='/status/']"  # link that contains /status/<id>

# ---------------------------------------------------------------------------
# Action bar buttons (inside a tweet article)
# ---------------------------------------------------------------------------

REPLY_BUTTON = '[data-testid="reply"]'
REPOST_BUTTON = '[data-testid="retweet"]'
UNREPOST_BUTTON = '[data-testid="unretweet"]'
LIKE_BUTTON = '[data-testid="like"]'
UNLIKE_BUTTON = '[data-testid="unlike"]'
SHARE_BUTTON = '[data-testid="share"]'
BOOKMARK_BUTTON = '[data-testid="bookmark"]'

# ---------------------------------------------------------------------------
# Repost / quote drop-down menu
# ---------------------------------------------------------------------------

REPOST_MENU_ITEM = '[data-testid="retweetConfirm"]'
QUOTE_MENU_ITEM = '[role="menuitem"]:has-text("Quote")'

# ---------------------------------------------------------------------------
# Compose (new post / reply / quote)
# ---------------------------------------------------------------------------

COMPOSE_TEXTBOX = '[data-testid="tweetTextarea_0"]'
COMPOSE_POST_BUTTON = '[data-testid="tweetButton"]'
COMPOSE_INLINE_POST_BUTTON = '[data-testid="tweetButtonInline"]'
COMPOSE_FILE_INPUT = 'input[accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime"]'
COMPOSE_MEDIA_BUTTON = '[data-testid="fileInput"]'

# ---------------------------------------------------------------------------
# Reply dialog (in-thread)
# ---------------------------------------------------------------------------

REPLY_DIALOG = '[data-testid="inline_reply_offscreen"]'
REPLY_TEXTBOX = '[data-testid="tweetTextarea_0"]'
REPLY_POST_BUTTON = '[data-testid="tweetButton"]'

# ---------------------------------------------------------------------------
# Repost indicator (in feed — "X reposted")
# ---------------------------------------------------------------------------

SOCIAL_CONTEXT = '[data-testid="socialContext"]'

# ---------------------------------------------------------------------------
# Profile page — x.com/{handle}
# ---------------------------------------------------------------------------

PROFILE_HEADER = '[data-testid="UserName"]'
PROFILE_BIO = '[data-testid="UserDescription"]'
PROFILE_LOCATION = '[data-testid="UserLocation"]'
PROFILE_URL = '[data-testid="UserUrl"]'
PROFILE_JOINED = '[data-testid="UserJoinDate"]'
PROFILE_VERIFIED = '[data-testid="icon-verified"]'
PROFILE_FOLLOWERS_LINK = 'a[href$="/verified_followers"], a[href$="/followers"]'
PROFILE_FOLLOWING_LINK = 'a[href$="/following"]'
PROFILE_EDIT_BUTTON = '[data-testid="editProfileButton"]'

# Stat spans inside the followers / following links
PROFILE_STAT_VALUE = "span > span"

# ---------------------------------------------------------------------------
# Profile edit page — x.com/settings/profile
# ---------------------------------------------------------------------------

EDIT_NAME_INPUT = 'input[name="displayName"]'
EDIT_BIO_TEXTAREA = 'textarea[name="description"]'
EDIT_LOCATION_INPUT = 'input[name="location"]'
EDIT_WEBSITE_INPUT = 'input[name="url"]'
EDIT_SAVE_BUTTON = '[data-testid="Profile_Save_Button"]'

# ---------------------------------------------------------------------------
# Navigation / confirmation
# ---------------------------------------------------------------------------

TOAST_NOTIFICATION = '[data-testid="toast"]'
PRIMARY_COLUMN = '[data-testid="primaryColumn"]'
BACK_BUTTON = '[data-testid="app-bar-back"]'

# ---------------------------------------------------------------------------
# Conversation thread (on a status page)
# ---------------------------------------------------------------------------

CONVERSATION_TWEET = 'article[data-testid="tweet"]'
SHOW_REPLIES_BUTTON = '[data-testid="cellInnerDiv"] [role="button"]:has-text("Show")'
