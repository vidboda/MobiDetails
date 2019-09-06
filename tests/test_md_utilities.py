import pytest
from flask import g, session
from MobiDetailsApp import md_utilities


@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.Arg34*', 'Arg34*'),
	('c.100C>T', '100C>T'),
	('g.6160C>T', '6160C>T'),
	('p.(Arg34*)', 'Arg34*',),
	('p.(Arg34*', 'Arg34*'),
	('p.(Arg34=', 'Arg34=')
))
def test_clean_var_name(client, variant_in, variant_out):
	test_var = md_utilities.clean_var_name(variant_in)
	assert test_var == variant_out

@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.R34X', 'Arg34*'),
	('p.(R34*', 'Arg34*'),
	('p.R34_E65del', 'Arg34_Glu65del'),
	('p.(R34Y)', 'Arg34Tyr',),
	('p.(R34_E65del)', 'Arg34_Glu65del'),
	('p.(R34=', 'Arg34=')
))
def test_one2three_fct(client, variant_in, variant_out):
	test_var = md_utilities.one2three_fct(variant_in)
	assert test_var == variant_out
	
@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.Arg34X', 'R34*'),
	('p.Arg34del', 'R34del'),
	('p.Arg34Ter', 'R34*'),
	('p.(Arg34*', 'R34*'),
	('p.Arg34_Glu65del', 'R34_E65del'),
	('p.(Arg34tyr)', 'R34Y',),
	('p.(Arg34_Glu65del)', 'R34_E65del'),
	('p.(Arg34=', 'R34='),
))
def test_three2one_fct(client, variant_in, variant_out):
	test_var = md_utilities.three2one_fct(variant_in)
	print(test_var)
	assert test_var == variant_out