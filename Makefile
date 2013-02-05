multissh.tar: *.py multissh
	mkdir -p _tar/multissh
	cp $^ _tar/multissh/
	tar cvzf multissh.tar -C _tar/ multissh
	rm -rf _tar

clean:
	rm *.pyc multissh.tar
