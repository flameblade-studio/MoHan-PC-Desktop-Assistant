# Privacy / 隱私說明

## Local by default

Tasks, ideas, settings, work sessions, conversations, memories, connector
metadata, permissions, workflows, and audit records are stored in the local
application-data directory. Verified backups are stored in its `backups`
subdirectory.

## Cloud processing

Cloud processing occurs only when a user enables the relevant feature:

- OpenAI receives text, audio, or tool-planning context needed for the request.
- Google, Microsoft, or GitHub receives API requests authorized through the
  user's own OAuth consent.
- Home Assistant receives local device requests.

The application does not make ChatGPT account history automatically available to
the assistant. Long-term memory is an explicit local database controlled by the
user.

## Camera

Camera presence detection is off by default. When enabled, the application
samples low-resolution brightness and movement locally. Frames are not stored or
uploaded. A visible status label remains active while the camera is in use.
Identity recognition is disabled unless a separate auditable local provider is
installed and the user explicitly enrolls identities.

## Remote access

Remote access is off by default. The optional mobile page uses a device token
kept in browser session storage. Remote screenshots contain only the application
window. Remote files must be inside a user allowlist and sensitive key, password,
credential, SSH, GnuPG, and application-data locations are blocked.

## User control

Users can view, edit, delete, and export memories; clear selected conversations;
revoke paired devices and OAuth tokens; disable connectors; remove allowlists;
stop the remote server; stop the camera; and use emergency stop at any time.

Portable `.mohan-profile` files contain the user's shared progress, including
conversations, memories, tasks, ideas, work history, reminders, workflows,
persona and general preferences. They do not contain DPAPI secrets, OAuth or
Home Assistant tokens, paired-device tokens, local allowlists or machine
permissions. These files can still contain private conversation and work
content, so they should be stored and transferred as private documents.
The manifest also contains random installation and snapshot identifiers used
to prevent accidental repeat/older imports. These identifiers do not contain
the Windows account name or computer name.
