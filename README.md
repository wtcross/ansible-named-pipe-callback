# ansible-named-pipe-callback
> An Ansible callback plugin that simply writes playbook events to a named pipe.

This plugin makes use of the following env variables:
`ANSIBLE_NAMED_PIPE` (required): path to the named pipe where status updates
                                 should be written
`ANSIBLE_SESSION_ID` (optional): id for this session, defaults to a uuid
