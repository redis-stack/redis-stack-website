document.addEventListener("DOMContentLoaded", function() {
	// Mobile menu stuff.
	const mobileIcon = document.querySelector( '.mobile-icon' );

	if ( mobileIcon ) {
		mobileIcon.addEventListener( 'click', () => {
			document.body.classList.toggle('menu-open');

			mobileIcon.classList.toggle( 'engage' );

			const theMenu = document.querySelector( '.navbar-nav' );

			if ( theMenu ) {
				theMenu.classList.toggle( 'engage' );
			}
		} );
	}
} );
