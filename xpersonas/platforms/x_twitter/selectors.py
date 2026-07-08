"""X/Twitter DOM selectors: single source of truth."""

TWEET_ARTICLE = 'article[data-testid="tweet"]'
TWEET_TEXT = '[data-testid="tweetText"]'
TWEET_USER_NAME = '[data-testid="User-Name"]'
TWEET_TIMESTAMP = "time"
TWEET_PERMALINK = f"{TWEET_USER_NAME} a[href*='/status/']"

REPLY_BUTTON = '[data-testid="reply"]'
REPOST_BUTTON = '[data-testid="retweet"]'
UNREPOST_BUTTON = '[data-testid="unretweet"]'
LIKE_BUTTON = '[data-testid="like"]'
UNLIKE_BUTTON = '[data-testid="unlike"]'
SHARE_BUTTON = '[data-testid="share"]'
BOOKMARK_BUTTON = '[data-testid="bookmark"]'

REPOST_MENU_ITEM = '[data-testid="retweetConfirm"]'
QUOTE_MENU_ITEM = '[role="menuitem"]:has-text("Quote")'

COMPOSE_TEXTBOX = '[data-testid="tweetTextarea_0"]'
COMPOSE_POST_BUTTON = '[data-testid="tweetButton"]'
COMPOSE_INLINE_POST_BUTTON = '[data-testid="tweetButtonInline"]'

REPLY_DIALOG = '[data-testid="inline_reply_offscreen"]'
REPLY_TEXTBOX = '[data-testid="tweetTextarea_0"]'

SOCIAL_CONTEXT = '[data-testid="socialContext"]'

PROFILE_HEADER = '[data-testid="UserName"]'
PROFILE_BIO = '[data-testid="UserDescription"]'
PROFILE_VERIFIED = '[data-testid="icon-verified"]'

TOAST_NOTIFICATION = '[data-testid="toast"]'
PRIMARY_COLUMN = '[data-testid="primaryColumn"]'
