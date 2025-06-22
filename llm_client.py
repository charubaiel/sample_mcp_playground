
import httpx
import json
import asyncio
from dataclasses import dataclass
from mcp_client import MCPClient

@dataclass
class ModelRaw:
    api_base:str
    model_id:str = None
    max_tokens:int=2048
    temperature:float=0.6
    repetition_penalty:float=1.4
    SYSTEM_PROMPT:str = ''
    mcp_client:MCPClient = None
    
    def __post_init__(self):
        # init model 
        if self.model_id is None:
            model_name = httpx.get(f'{self.api_base}/models').json()['data'][0]['id']
            self.model_id = f'{model_name}'
            
    async def __init_mcp__(self):
        # init mcp connection
        tools_ = await self.mcp_client.list_tools()
        self.available_tools = [{'type':'function','function':json.loads(tool.model_dump_json())} for tool in tools_.tools]

    async def ainvoke(self,messages:list[dict],system_propmt = None,tools=None,**kwargs):
        # base functions alike chat/completion wrapper
        tools_args = {
            'tools':self.available_tools,
            'tool_choice':'auto',
        }
            
        if system_propmt is None :
            system_propmt = self.SYSTEM_PROMPT

        if tools is not None :
            tools_args['tools'] = tools

        request_messages = [
            {
                'role':'system',
                'content':system_propmt,
            }
        ] + messages

        response = httpx.post(f'{self.api_base}/chat/completions',json=
                        {
                        'model':self.model_id,
                        'messages':request_messages,
                        'temperature':kwargs.get('temperature',self.temperature),
                        **tools_args,
                        **kwargs
                    },
                    timeout=90).json()
        
        return response
    
    async def agather_func_calls(self,requested_tools:list):
        func_answers = await asyncio.gather(*[self.mcp_client.invoke_tool(
                                                        name = tool['function']['name'],
                                                        arguments = json.loads(tool['function']['arguments']),
                                                        )
                                            for tool in requested_tools])
        print([tool['function']['name'] for tool in requested_tools])
        return {'role':'tool','content':'\n\n'.join([func.content for func in func_answers])}
    
    async def precess_request(self,request:str,steps_limit:int = 5):

        messages = [
            {'role':'user','content':request}
        ]
        n = 0
        tools = None
        finish_reason = 'initial_question'
        while finish_reason not in ('stop','length'):
            if steps_limit<n:
                tools = []

            response = await self.ainvoke(messages,tools=tools)
            try:
                finish_reason = response['choices'][0]['finish_reason']
            except Exception as e:
                print(response,'\n\n'+str(e))
            print(f'Step {n} : {finish_reason}')
                

            if response['choices'][0]['message']['tool_calls']: 
                messages.append(await self.agather_func_calls(response['choices'][0]['message']['tool_calls']))  
            else:
                messages.append({'role':'assistant','content':response['choices'][0]['message']['content']})
                         
            n+=1
        return response
        
    