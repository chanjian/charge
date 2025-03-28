# country_counter = {}
#
# def addone(country):
#     if country in country_counter:
#         country_counter[country] +=1
#
#     else:
#         country_counter[country] = 1
#
#
# addone('China')
# addone('Japan')
# addone('China')
# print(len(country_counter))


# def doff(arg1,*args):
#     print(type(args))
#
# doff('applea','bananas','cherry')

arr = [1,2,3]
def bar():

    arr += [5]

bar()
print(arr)