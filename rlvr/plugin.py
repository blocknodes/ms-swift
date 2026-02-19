import asyncio
import os
import random
import re
import textwrap
from collections import Counter
from copy import deepcopy
from typing import Dict, List, Union

import json
import torch

from swift.llm import PtEngine, RequestConfig, RolloutInferRequest, Template, to_device
from swift.llm.infer.protocol import ChatCompletionResponse, ChatCompletionResponseChoice
from swift.plugin import ORM, AsyncORM, orms, rm_plugins
# register context manager(used in gym training)
from swift.plugin.context_manager import ContextManager, context_managers
from swift.plugin.env import Env, envs
from swift.plugin.multi_turn import MultiTurnScheduler, multi_turns
from swift.plugin.rm_plugin import DefaultRMPlugin
from swift.utils import get_logger
import json

logger = get_logger()
"""
TO CUSTOMIZE REWARD FUNCTION:
    Step 1: Define a Reward Class
        Implement your custom reward calculation logic within the __call__ method.
        The method accepts the model's output completions and dataset columns (passed as kwargs) as input parameters.

    Step 2: Add your reward function to the orms registry:
        orms['my_reward_function'] = MyRewardFunction

    Step 3: Configure the Arguments
        Run the script with:
        --external_plugins /path/to/plugin.py \
        --reward_funcs my_reward_function
"""


# For additional reward functions, refer to swift/plugin/orm.py.
class JsonPrecision(ORM):

    def __call__(self, completions,target, **kwargs) -> List[float]:
        """
        Evaluates completions based on Mathematical correctness of the answer

        Args:
            completions (list[str]): Generated outputs
            target (list[str]): Expected answers
            nums (list[str]): Available numbers

        Returns:
            list[float]: Reward scores
        """
        rewards = []
        for completion, gt in zip(completions, target):
            try:
                # Check if the format is correct
                #print(completion,gt)

                content = json.loads(completion)
                gt = json.loads(gt)
                query=gt.pop('query')

                # compare target
                if 'target' in content.keys():
                    targets=content['target']
                else:
                    targets=content['targets']
                #targets=content['target']
                if 'target' in gt.keys():
                    gt_targets=gt['target']
                else:
                    gt_targets=gt['targets']

                if not set(gt_targets).issubset(set(targets)):
                    raise ValueError(f"query:{query}\nct targets:{targets}\ngt targets:{gt_targets}")
                # compare condition

                conditions = content['conditions']
                gt_conditions = gt['conditions']



                condition_key_set = set([item['property_name'] for item in conditions])
                gt_conditions_key_set = set([item['property_name'] for item in gt_conditions])
                if not condition_key_set==gt_conditions_key_set:
                    raise ValueError(f"query:{query}\ncp cond set:{condition_key_set}\ngt cond set:{gt_conditions_key_set}")
                for item in conditions:
                    for gt_item in gt_conditions:
                        if item['property_name'] == gt_item['property_name']:
                            if item['property_name'] == 'salesBrandName':
                                if item['property_value'] == '海信':
                                    item['property_value'] = 'Hisense'
                                if gt_item['property_value'] == '海信':
                                    gt_item['property_value'] = 'Hisense'
                            if item['property_name'] == 'actualSalesDate':
                                if item['property_value'] in query:
                                    break
                                if gt_item['op'] != item['op']:
                                    logger.warning(f"query:{query}\n condition:{item} \ngt_condition:{gt_item}")
                                    gt_item['op'] = item['op']
                            if item['property_value'] != gt_item['property_value'] or item['op'] != gt_item['op']:
                                raise ValueError(f"query:{query}\n condition:{item} \ngt_condition:{gt_item}")


                #print(completion,gt)
                rewards.append(1.0)
            except Exception as e:
                # If evaluation fails, reward is 0
                logger.error(f"评估失败，异常信息：{e}\n\n附：cp:{completion}\ngt:{gt}\n###########")
                #logger.info(completion,gt)
                rewards.append(0.0)
        return rewards


orms['json_precision'] = JsonPrecision


