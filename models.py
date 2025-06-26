# Model configurations
AVAILABLE_MODELS = {
    # Claude Models
    '@sonnet3.5': 'anthropic/claude-3-5-sonnet-20240620',
    '@sonnet3.7': 'anthropic/claude-3-7-sonnet-20250219',
    '@sonnet4': 'anthropic/claude-sonnet-4-20250514',
    '@opus3': 'anthropic/claude-3-opus-20240229',
    '@opus4': 'anthropic/claude-opus-4-20250514',
    '@haiku3': 'anthropic/claude-3-haiku-20240307'
}

# Model descriptions for UI
MODEL_DESCRIPTIONS = [
    # Claude models
    {'tag': '@sonnet3.5', 'desc': 'Claude 3.5 Sonnet'},
    {'tag': '@sonnet3.7', 'desc': 'Claude 3.7 Sonnet'},
    {'tag': '@sonnet4', 'desc': 'Claude 4 Sonnet'},
    {'tag': '@opus3', 'desc': 'Claude 3 Opus'},
    {'tag': '@opus4', 'desc': 'Claude 4 Opus'},
    {'tag': '@haiku3', 'desc': 'Claude 3 Haiku'}
]