PROJECT_NAME = ncvoter

deployment/keys/%.pub.ssh:
	# Generate SSH deploy key for a given environment
	ssh-keygen -t rsa -b 4096 -f $*.priv -C "$*@${PROJECT_NAME}"
	@mv $*.priv.pub $@

staging-deploy-key: deployment/keys/staging.pub.ssh

production-deploy-key: deployment/keys/production.pub.ssh
