# Model configurations
AVAILABLE_MODELS = {
    # OpenAI Models
    '@gpt4': 'openai/gpt-4o',
    '@gpt3': 'openai/gpt-3.5-turbo',
    '@gpt4.1': 'openai/gpt-4.1',
    '@gpt4.1-mini': 'openai/gpt-4.1-mini',
    '@gpt4.1-nano': 'openai/gpt-4.1-nano',
    '@o4-mini': 'openai/o4-mini',
    '@o3-mini': 'openai/o3-mini',
    '@o3': 'openai/o3',
    '@o1-mini': 'openai/o1-mini',
    
    # Claude Models
    '@claude': 'anthropic/claude-3-5-sonnet-20240620',
    '@claude4': 'anthropic/claude-sonnet-4-20250514',
    '@opus4': 'anthropic/claude-opus-4-20250514',
    '@sonnet4': 'anthropic/claude-sonnet-4-20250514',
    '@sonnet3.7': 'anthropic/claude-3-7-sonnet-20250219',
    '@sonnet3.5': 'anthropic/claude-3-5-sonnet-20240620',
    '@haiku': 'anthropic/claude-3-haiku-20240307',
    '@opus': 'anthropic/claude-3-opus-20240229'
}

# Model descriptions for UI
MODEL_DESCRIPTIONS = [
    # Claude models
    {'tag': '@claude', 'desc': 'Claude 3.5 Sonnet'},
    {'tag': '@claude4', 'desc': 'Claude 4 Sonnet'},
    {'tag': '@opus4', 'desc': 'Claude Opus 4'},
    {'tag': '@sonnet4', 'desc': 'Claude Sonnet 4'},
    {'tag': '@sonnet3.7', 'desc': 'Claude 3.7 Sonnet'},
    {'tag': '@sonnet3.5', 'desc': 'Claude 3.5 Sonnet'},
    {'tag': '@haiku', 'desc': 'Claude 3 Haiku'},
    {'tag': '@opus', 'desc': 'Claude 3 Opus'},
    # OpenAI models
    {'tag': '@gpt4', 'desc': 'OpenAI GPT-4'},
    {'tag': '@gpt3', 'desc': 'GPT-3.5 Turbo'},
    {'tag': '@gpt4.1', 'desc': 'GPT-4.1'},
    {'tag': '@gpt4.1-mini', 'desc': 'GPT-4.1 Mini'},
    {'tag': '@gpt4.1-nano', 'desc': 'GPT-4.1 Nano'},
    {'tag': '@o4-mini', 'desc': 'O4 Mini'},
    {'tag': '@o3-mini', 'desc': 'O3 Mini'},
    {'tag': '@o3', 'desc': 'O3'},
    {'tag': '@o1-mini', 'desc': 'O1 Mini'}
]