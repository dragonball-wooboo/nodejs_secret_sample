import boto3
import openpyxl
import os
import json
import csv
from pprint import pprint as pp

#file을 저장하기 위한 변수
file_path = "output.txt"
file_mode = "a"

# iam 서비스를 위한 boto3 client 생성
iam = boto3.client('iam')

# list_users 메소드에 대한 paginator 생성
paginator = iam.get_paginator('list_users')

# iam list 유저 변수 생성
iam_user = []

# custom policy 유저 변수 생성
custom_policy_name = []

# group name 유저 변수 생성 
group_name = []

# group name 안에 들어가 있는 policy 생성 
policy_name_in_group = []

# csv파일에 저장해야 하는 list 변수 생성
final_result =[]

# csv 파일 이름
filename = 'aws_iam_list.csv'
excel_file_name =  'aws_iam_list.xlsx'

# list 형태의 변수를 엑셀 파일로 출력 할 수 있게 worksheet를 만드는 변수 생성
workbook = openpyxl.Workbook()
worksheet = workbook.active

# iam policy를 인자값으로 던져 주면 iam policy의 body_statement 정책을 비교를 해서 아래 조건일 경우를 전부 더해서 return해줍니다.
# 값이 1 일 경우에는 Condition 이 없습니다.
# 값이 0.5 일 경우에는 Condition 이 있지만 sourceIP가 0.0.0.0/0 입니다.
# 값이 0 일 경우에는 Condition 이 있고 sourceIP가 0.0.0.0/0이 아닙니다.
def get_policy_body_statement(arn, version_id=None):
    iam = boto3.resource('iam')
    """ Return IAM Policy JSON body """

    if version_id:
        version = iam.PolicyVersion(arn, version_id)
    # iam policy에는 여러 버전이 존재한다. default version의 정책을 가져오려면 아래 구문으로 동작이 되야 한다.
    else:
        policy = iam.Policy(arn)
        version = policy.default_version
    # iam policy의 statement에 condition이 있는지 체크하는 부분. 
    condition = 0

    list_main = []

    # iam policy의 statement에 두개 이상이 있을 경우에는 dictionary [ ] 대괄호 안에 { } 중괄호로 개별 statement로 구별을 한다. 
    # statement하나에 단 하나만 있을 경우에는 { } 형태로 묶여 있어서 dictinary 형식으로 구성 되어 있는데 이럴 때 아래 condition조건을 탈수가 없다. 그래서 list 형식으로 변환을 해줘야 한다. 
    if isinstance(version.document['Statement'], dict):
        list_main.append(version.document['Statement'])
    else:
        list_main = version.document['Statement']

    for policy in list_main:
        if "Resource" in policy:
            if policy["Effect"] == "Allow": 
                if "Condition" in policy:
                    if "IpAddress" in policy["Condition"] and "aws:SourceIp" in policy["Condition"]["IpAddress"] and policy["Condition"]["IpAddress"]["aws:SourceIp"] == "0.0.0.0/0":
                        # print("condition이 있지만 sourceIP가 0.0.0.0/0 입니다.")
                        condition += 0.01
                    elif "ForAnyValue:IpAddress" in policy["Condition"] and "aws:SourceIp" in policy["Condition"]["ForAnyValue:IpAddress"] and policy["Condition"]["ForAnyValue:IpAddress"]["aws:SourceIp"] == "0.0.0.0/0":
                        # print("condition이 있지만 ForAnyValue:IpAddress sourceIP가 0.0.0.0/0 입니다.")
                        condition += 0.01
                    else:
                        # print("condition이 있고 sourceIP가 0.0.0.0/0이 아닙니다.")
                        condition += 0
                else:
                    # print("Condition이 없습니다.")
                    condition += 1
            else:
                condition += 0 
    return condition


# policy를 인자값으로 주면 arn을 리턴 해 주는 함수
def get_policy_arn(policy_name):
    iam = boto3.client('iam')
    list_polices_paginator = iam.get_paginator('list_policies')
    for page in list_polices_paginator.paginate():
        for policy in page['Policies']:
            if policy['PolicyName'] == policy_name:
                return policy['Arn']



for response in paginator.paginate():
    for user in response['Users']:
        # iam user_name을 하나씩 추가.
        iam_user = user['UserName']
        # 하나의 유저에 대한 user list 와 userpolicy를 저장하는 배열 변수
        Row_Result = []
        # AccessKeyId를 사용을 하는 지 안하는 지에 대한 변수
        AccessKeyId_flag = 0
        # pagenation interface를 통해서 accesskey를 사용하는 유저들의 리스트를 뽑아보자.
        access_key_paginator = iam.get_paginator('list_access_keys')
        # iam_user값을 받아와서 해당 이름으로 사용하고 있는 AccessKeyMetadata, IsTruncated, ResponseMetadata 추출
        for check_access_key_users in access_key_paginator.paginate(UserName=iam_user):
            # 그 유저의 위의 정보값 중에 우리가 필요한 AccessKeyMetadata값만 추출
            for check_access_key_user in check_access_key_users['AccessKeyMetadata']:
                # AccessKeyMetadata에서 AccessKeyId를 사용을 하는 사람을 체크
                if check_access_key_user['AccessKeyId'] is not None:
                    AccessKeyId_flag = 1
                    # iam_user 출력
                    print(f"iam_user: {iam_user}")
                    # Row_Result list 에 iam_user_name 추가
                    Row_Result.append(iam_user)
                    # 이미 attached 된 user policy 를 받아오는 iam cusstom managed policy paginator 추가
                    policy_paginator = iam.get_paginator('list_attached_user_policies')
                    # iam user의 group 을 받아오는 group name을 가져오는 policy paginator 추가
                    group_list_group_paginatgor = iam.get_paginator('list_groups_for_user')
                    # iam inline policy를 가져오는 policy paginator 추가
                    get_inline_policy_paginator = iam.get_paginator('list_user_policies')
                    # 해당 iam_user의 PolicyNames, IsTruncated, NextToken 값을 추출
                    for inline_policy in get_inline_policy_paginator.paginate(UserName=iam_user):
                        # 그 유저의 위의 정보값 중에 우리가 필요한 PolicyNames 추출
                        for in_policy in inline_policy['PolicyNames']:
                            Row_Result.append(in_policy)
                            # ---------추가(2023-04-14(금)------
                            # policy를 인자로 던져서->arn가져오고->arn으로 body_statement를 가져와서 statement 구문안에 condition이 있는지 없는지 체크-> condition이 있어도 0.0.0.0일 경우에도 체크
                            POLICY_ARN = get_policy_arn(in_policy)
                            print(f"POLICY_ARN : {POLICY_ARN}")
                            if isinstance(POLICY_ARN, type(None)):
                                Row_Result.append("★")
                            else:
                                body = get_policy_body_statement(get_policy_arn(in_policy))
                                Row_Result.append(body)
                            # --------------------------------
                    # 해당 iam_user의 AttachedPolicies, IsTruncated, NextToken 값을 추출 
                    for policies in policy_paginator.paginate(UserName=iam_user):
                    # 그 유저의 위의 정보값 중에 우리가 필요한 AttachedPolicies만 추출
                        for policy in policies['AttachedPolicies']:
                            # iam custommanged policy 하나씩 추가
                            custom_policy_name = policy['PolicyName']
#                           print(f"Customer_direct_managed_policy : {custom_policy_name}")
                            # Row_Result list 에 custom_policy_name 추가
                            Row_Result.append(custom_policy_name)
                            # ---------추가(2023-04-14(금)------
                            # policy를 인자로 던져서->arn가져오고->arn으로 body_statement를 가져와서 statement 구문안에 condition이 있는지 없는지 체크-> condition이 있어도 0.0.0.0일 경우에도 체크
                            POLICY_ARN = get_policy_arn(custom_policy_name)
                            print(f"POLICY_ARN : {POLICY_ARN}")
                            if isinstance(POLICY_ARN, type(None)):
                                Row_Result.append("★")
                            else:
                                body = get_policy_body_statement(POLICY_ARN)
                                Row_Result.append(body)
                            # --------------------------------
                        # 해당 iam_user의 Groups, IsTruncated, NextToken 값을 추출
                    for group_policies in group_list_group_paginatgor.paginate(UserName=iam_user):
                        # 그 유저의 위의 정보값 중에 우리가 필요한 Groups 추출
                        for group in group_policies['Groups']:
                            # iam aws managed policy 하나씩 추가
                            group_name=group['GroupName']
                            # group name 출력 
#                               print(f"IAM_group_policy: {group_name}")
                            # 이미 attached 된 group 에서 policy를 가져오는 paginator 추가.
                            get_policy_from_group_policy_paginator = iam.get_paginator('list_attached_group_policies')
                            # 해당 group_name의 AttachedPolicies, IsTruncated, Marker 값을 추출
                            for get_policy in get_policy_from_group_policy_paginator.paginate(GroupName=group_name):
                                # 그 그룹의 위의 정보값 중에 우리가 필요한 AttachedPolicies 추출
                                for ge_policy in get_policy['AttachedPolicies']:
                                    # group 안에 있는 policy 하나씩 추가
                                    policy_name_in_group = ge_policy['PolicyName']
#                                       print(f"IAM_group_policy's_group: {policy_name_in_group}")
                                    # Row_Result list 에 custom_policy_name 추가
                                    Row_Result.append(policy_name_in_group)
                                    # ---------추가(2023-04-14(금)------
                                    # policy를 인자로 던져서->arn가져오고->arn으로 body_statement를 가져와서 statement 구문안에 condition이 있는지 없는지 체크-> condition이 있어도 0.0.0.0일 경우에도 체크
                                    POLICY_ARN = get_policy_arn(policy_name_in_group)
                                    print(f"POLICY_ARN : {POLICY_ARN}")
                                    if isinstance(POLICY_ARN, type(None)):
                                        Row_Result.append("★")
                                    else:
                                        body = get_policy_body_statement(get_policy_arn(policy_name_in_group))
                                        Row_Result.append(body)
                                    # --------------------------------
        # AccessKeyId를 사용을 하는 유저들에 대한 Row_Result를 최종 final_resulet에 반영 하는 부분
        if AccessKeyId_flag == 1:
            # Row_Result안에 있는 policy를 중복 제거를 하기 위해서 dictionary로 변경->다시 list로 변경(dictionary는 중복값이 들어갈수 없음 
            ##list안의 중복 제거(**username과 동일한 iam policy가 있을 수 있으니가 0번째가 아닌 1번째 요소부터 중복 제거 ) 

#            user = Row_Result[0]
#            list_new_converted = []
#            i = 1
#            while i < len(Row_Result):
#                list_new_converted.append(str(Row_Result[i]) + "|" + str(Row_Result[i+1]))
#                i = i + 2
#            list_duplicated_removed = list(set(list_new_converted))
#            list_new_converted = [user]
#
#            for item in list_duplicated_removed:
#                list_splitted_subitem = item.split("|")
#                for splited_item in list_splitted_subitem:
#                    list_new_converted.append(splited_item)

            # list안의 중복 제거(**username과 동일한 iam policy가 있을 수 있으니가 0번째가 아닌 1번째 요소부터 중복 제거 )
            print(Row_Result)
            final_result.append(Row_Result)
            
            with open(file_path, file_mode) as file:
                for item in Row_Result:
                    file.write(str(item) + "|")
                file.write("\n")  

# print(final_result)

with open(filename, 'w') as f:
    for item in final_result:
        f.write("%s\n" % item)

# final_result list의 결과를 루프를 돌아서 worksheet에 row 하나식 append 한다.
for row in final_result:
    worksheet.append(row)

# worksheet 파일 저장
workbook.save(excel_file_name)

# 파일 close
file.close()
f.close()

