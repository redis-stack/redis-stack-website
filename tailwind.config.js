const { red } = require('tailwindcss/colors');
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
      typography: (theme) => (  {
        DEFAULT: {
          css: {
            color: theme('colors.slate.600'),
            a: {
              transition: '.2s all',
              color: theme('colors.indigo.600'),
              textDecorationColor: theme('colors.indigo.300'),
              textDecorationThickness: '1px',
              textUnderlineOffset: '1px',
              '&:hover': {
                color: theme('colors.indigo.400'),
              },
            },
          },
        },
        lg: {
          css: {
            lineHeight: '1.6',
          },
        },
      }),
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    plugin(function({ addComponents, theme }) {
			const buttons = {
				'.button-xs, .button-sm, .button, .button-lg, .button-xl, .button-2xl': {
					display: 'inline-flex',
					alignItems: 'center',
					justifyContent: 'center',
					fontWeight: '600',
					letterSpacing: theme('letterSpacing.normal'),
					borderRadius: theme('borderRadius.lg'),
					whiteSpace: 'nowrap',
					transition: '.2s all',
				},
				'.button-xs': {
					fontSize: theme('fontSize.sm'),
					paddingLeft: theme('spacing.1'),
					paddingRight: theme('spacing.1'),
					height: '30px'
				},
				'.button-sm': {
					fontSize: theme('fontSize.sm'),
					paddingLeft: theme('spacing.3'),
					paddingRight: theme('spacing.3'),
					height: '34px'
				},
				'.button': {
					fontSize: theme('fontSize.sm'),
					paddingLeft: theme('spacing.3'),
					paddingRight: theme('spacing.3'),
					height: '38px'
				},
				'.button-lg': {
					fontSize: theme('fontSize.sm'),
					paddingLeft: theme('spacing.4'),
					paddingRight: theme('spacing.4'),
					height: '42px'
				},
				'.button-xl': {
					fontSize: theme('fontSize.base'),
					paddingLeft: theme('spacing.5'),
					paddingRight: theme('spacing.5'),
					height: '48px'
				},
				'.button-2xl': {
					fontSize: theme('fontSize.lg'),
					paddingLeft: theme('spacing.6'),
					paddingRight: theme('spacing.6'),
					height: '60px'
				}
      };
      addComponents([ buttons ]);
		})
  ],
};