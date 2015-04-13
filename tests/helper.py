#encoding: utf8

def accept_test_helper(regex,cases):
    for s,expected in cases:
        result = regex.accept(s) 
        print("regex:{regex}, string:{s}, result:{result}, expected:{expected}, {ok}".format(
            regex=regex.description,
            s=s,
            result=result,
            expected=expected,
            ok='OK' if result == expected else 'FAILED'))
        assert result == expected

