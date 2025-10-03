"""
2025.10.03
https://www.bigmodel.cn/dev/api/normal-model/glm-4

https://open.bigmodel.cn/pricing

"""
import time

from conf import DEF_LLM_ZHIPUAI
from conf import DEF_MODEL_ZHIPUAI

from zhipuai import ZhipuAI


def get_glm_client():
    client = ZhipuAI(api_key=DEF_LLM_ZHIPUAI)
    return client


def gene_by_llm_once(s_prompt):
    """
    Return:
        None: Fail to generate msg by llm
        string: generated content by llm
    """
    # s_model = "glm-4-air"
    # s_model = "glm-4-plus"
    s_model = DEF_MODEL_ZHIPUAI
    client = get_glm_client()
    response = client.chat.asyncCompletions.create(
        model=s_model,  # 请填写您要调用的模型名称
        messages=[
            {
                "role": "user",
                "content": s_prompt
            }
        ],
    )
    task_id = response.id
    task_status = ''
    get_cnt = 0

    while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= 40: # noqa
        result_response = client.chat.asyncCompletions.retrieve_completion_result(id=task_id) # noqa
        # print(result_response)
        task_status = result_response.task_status

        if task_status == 'SUCCESS':
            s_cont = result_response.choices[0].message.content
            return s_cont

        time.sleep(2)
        get_cnt += 1

    return None


def gene_by_llm(s_prompt, max_retry=3):
    """
    Return:
        None: Fail to generate msg by llm
        string: generated content by llm
    """
    n_try = 0
    while n_try < max_retry:
        n_try += 1
        s_cont = gene_by_llm_once(s_prompt)
        if not s_cont:
            continue
        return s_cont
    return None


if __name__ == "__main__":
    """
    """
    pass


"""
# noqa
"""
