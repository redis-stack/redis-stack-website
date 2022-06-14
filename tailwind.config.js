const defaultTheme = require('tailwindcss/defaultTheme');
const plugin = require('tailwindcss/plugin');

module.exports = {
  content: ["content/**/*.md", "layouts/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
				sans: [ 'Inter', ...defaultTheme.fontFamily.sans ],
				mono: [ 'SF Mono', ...defaultTheme.fontFamily.mono ],
				display: [ 'Inter Display', ...defaultTheme.fontFamily.sans ],
			},
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    plugin(function({ addComponents, theme }) {
			const buttons = {
				'.button-xs, .button-sm, .button, .button-lg, .button-xl, .button-2xl': {
					display: 'inline-flex',
					'align-items': 'center',
					'justify-content': 'center',
					'font-weight': '600',
					'letter-spacing': theme('letterSpacing.normal'),
					'border-radius': theme('borderRadius.lg'),
					'white-space': 'nowrap',
					transition: '.2s all',
				},
				'.button-xs': {
					'font-size': theme('fontSize.sm'),
					'padding-left': theme('spacing.1'),
					'padding-right': theme('spacing.1'),
					height: '30px'
				},
				'.button-sm': {
					'font-size': theme('fontSize.sm'),
					'padding-left': theme('spacing.3'),
					'padding-right': theme('spacing.3'),
					height: '34px'
				},
				'.button': {
					'font-size': theme('fontSize.sm'),
					'padding-left': theme('spacing.3'),
					'padding-right': theme('spacing.3'),
					height: '38px'
				},
				'.button-lg': {
					'font-size': theme('fontSize.sm'),
					'padding-left': theme('spacing.4'),
					'padding-right': theme('spacing.4'),
					height: '42px'
				},
				'.button-xl': {
					'font-size': theme('fontSize.base'),
					'padding-left': theme('spacing.5'),
					'padding-right': theme('spacing.5'),
					height: '48px'
				},
				'.button-2xl': {
					'font-size': theme('fontSize.lg'),
					'padding-left': theme('spacing.6'),
					'padding-right': theme('spacing.6'),
					height: '60px'
				}
      };
      addComponents([ buttons ]);
		})
  ],
};